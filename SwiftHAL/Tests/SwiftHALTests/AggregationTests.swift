import XCTest
@testable import SwiftHAL
import Foundation

final class AggregationTests: XCTestCase {
    var calculator: MetricsCalculator!
    var tempDir: URL!

    override func setUp() {
        calculator = MetricsCalculator()
        tempDir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try! FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
    }

    override func tearDown() {
        try? FileManager.default.removeItem(at: tempDir)
    }

    func writeFixture(_ name: String, content: String) -> URL {
        let url = tempDir.appendingPathComponent(name)
        try! content.write(to: url, atomically: true, encoding: .utf8)
        return url
    }

    func test_totals_mergeDistinctOperators() throws {
        // File 1: let x = 1 + 2
        let file1 = writeFixture("file1.swift", content: "let x = 1 + 2")
        let result1 = try calculator.calculateWithSets(for: file1)

        // File 2: var y = 3 - 4
        let file2 = writeFixture("file2.swift", content: "var y = 3 - 4")
        let result2 = try calculator.calculateWithSets(for: file2)

        // Manually merge for expected totals
        // Distinct operators: let, =, +, var, - (5 total, = is shared)
        // Total operators: let, =, +, var, =, - (6 total)

        let totals = aggregateTotals([result1, result2])

        XCTAssertEqual(totals.n1, 5, "Distinct operators: let, =, +, var, -")
        XCTAssertEqual(totals.N1, 6, "Total operators")
    }

    func test_totals_mergeDistinctOperands() throws {
        let file1 = writeFixture("file1.swift", content: "let x = 1")
        let result1 = try calculator.calculateWithSets(for: file1)

        let file2 = writeFixture("file2.swift", content: "let x = 2")
        let result2 = try calculator.calculateWithSets(for: file2)

        // Distinct operands: x (shared), 1, 2
        // Total operands: x, 1, x, 2

        let totals = aggregateTotals([result1, result2])

        XCTAssertEqual(totals.n2, 3, "Distinct operands: x, 1, 2")
        XCTAssertEqual(totals.N2, 4, "Total operands")
    }

    func test_totals_pathSetToTOTALS() throws {
        let file1 = writeFixture("file1.swift", content: "let x = 1")
        let result1 = try calculator.calculateWithSets(for: file1)

        let totals = aggregateTotals([result1])

        XCTAssertEqual(totals.path, "TOTALS")
    }

    func test_totals_calculatedMetricsWork() throws {
        let file1 = writeFixture("file1.swift", content: "let x = 1")
        let result1 = try calculator.calculateWithSets(for: file1)

        let totals = aggregateTotals([result1])

        // Should have valid calculated metrics
        XCTAssertGreaterThan(totals.vocabulary, 0)
        XCTAssertGreaterThan(totals.length, 0)
        XCTAssertGreaterThan(totals.volume, 0)
    }
}
