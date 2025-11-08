import XCTest
@testable import SwiftHAL
import Foundation

final class OutputFormatTests: XCTestCase {

    // JSON OUTPUT TESTS

    func test_jsonOutput_hasCorrectStructure() throws {
        var metrics1 = HalsteadMetrics(path: "test.swift")
        metrics1.n1 = 2
        metrics1.n2 = 2
        metrics1.N1 = 2
        metrics1.N2 = 2

        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 2
        totals.n2 = 2
        totals.N1 = 2
        totals.N2 = 2

        let json = formatAsJSON([metrics1], totals: totals)
        let data = json.data(using: .utf8)!
        let decoded = try JSONDecoder().decode(OutputSchema.self, from: data)

        XCTAssertEqual(decoded.files.count, 1)
        XCTAssertEqual(decoded.files[0].path, "test.swift")
        XCTAssertEqual(decoded.totals.path, "TOTALS")
    }

    func test_jsonOutput_includesAllMetrics() throws {
        var metrics1 = HalsteadMetrics(path: "test.swift")
        metrics1.n1 = 10
        metrics1.n2 = 20
        metrics1.N1 = 50
        metrics1.N2 = 100

        let json = formatAsJSON([metrics1], totals: metrics1)
        let data = json.data(using: .utf8)!
        let decoded = try JSONDecoder().decode(OutputSchema.self, from: data)

        let file = decoded.files[0]
        XCTAssertEqual(file.n1, 10)
        XCTAssertEqual(file.n2, 20)
        XCTAssertEqual(file.N1, 50)
        XCTAssertEqual(file.N2, 100)
        XCTAssertEqual(file.vocabulary, 30)
        XCTAssertEqual(file.length, 150)
        XCTAssertGreaterThan(file.volume, 0)
        XCTAssertGreaterThan(file.difficulty, 0)
    }

    // TABLE OUTPUT TESTS

    func test_tableOutput_hasHeaderRow() {
        var metrics1 = HalsteadMetrics(path: "test.swift")
        metrics1.n1 = 2
        metrics1.n2 = 2
        metrics1.N1 = 2
        metrics1.N2 = 2

        let table = formatAsTable([metrics1], totals: metrics1)

        XCTAssertTrue(table.contains("path") || table.contains("Path"))
        XCTAssertTrue(table.contains("volume") || table.contains("Volume"))
        XCTAssertTrue(table.contains("difficulty") || table.contains("Difficulty"))
    }

    func test_tableOutput_includesAllFiles() {
        var metrics1 = HalsteadMetrics(path: "file1.swift")
        metrics1.n1 = 2
        metrics1.n2 = 2
        metrics1.N1 = 2
        metrics1.N2 = 2

        var metrics2 = HalsteadMetrics(path: "file2.swift")
        metrics2.n1 = 3
        metrics2.n2 = 3
        metrics2.N1 = 3
        metrics2.N2 = 3

        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 5
        totals.n2 = 5
        totals.N1 = 5
        totals.N2 = 5

        let table = formatAsTable([metrics1, metrics2], totals: totals)

        XCTAssertTrue(table.contains("file1.swift"))
        XCTAssertTrue(table.contains("file2.swift"))
        XCTAssertTrue(table.contains("TOTALS"))
    }
}

// Helper schema for JSON decoding
struct OutputSchema: Decodable {
    let files: [FileMetrics]
    let totals: FileMetrics
}

struct FileMetrics: Decodable {
    let path: String
    let n1, n2, N1, N2: Int
    let vocabulary, length: Int
    let estimatedLength, volume, difficulty, effort, timeSeconds, riskScore: Double
}
