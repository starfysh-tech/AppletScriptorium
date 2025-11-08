import XCTest
@testable import SwiftHAL
import Foundation

final class AcceptanceTests: XCTestCase {
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

    // TEST 1: Empty file produces zero metrics
    func test_emptyFile_producesZeroMetrics() throws {
        let fixture = writeFixture("empty.swift", content: "")
        let metrics = try calculator.calculate(for: fixture)

        XCTAssertEqual(metrics.n1, 0, "Empty file: no distinct operators")
        XCTAssertEqual(metrics.N1, 0, "Empty file: no total operators")
        XCTAssertEqual(metrics.n2, 0, "Empty file: no distinct operands")
        XCTAssertEqual(metrics.N2, 0, "Empty file: no total operands")
        XCTAssertEqual(metrics.vocabulary, 0)
        XCTAssertEqual(metrics.volume, 0.0)
    }

    // TEST 2: Minimal code - manually verifiable counts
    func test_minimalCode_countsCorrectly() throws {
        let code = """
        let x = 1
        """
        // Manual count:
        // Operators: let, =     → n1=2, N1=2
        // Operands: x, 1        → n2=2, N2=2

        let fixture = writeFixture("minimal.swift", content: code)
        let metrics = try calculator.calculate(for: fixture)

        XCTAssertEqual(metrics.n1, 2, "Distinct operators: let, =")
        XCTAssertEqual(metrics.N1, 2, "Total operators: let, =")
        XCTAssertEqual(metrics.n2, 2, "Distinct operands: x, 1")
        XCTAssertEqual(metrics.N2, 2, "Total operands: x, 1")
    }

    // TEST 3: Duplicate identifiers
    func test_duplicateIdentifiers_increaseTotal_notDistinct() throws {
        let code = """
        let x = 1
        let y = x
        """
        // Operators: let(2x), =(2x)  → n1=2, N1=4
        // Operands: x(2x), 1, y      → n2=3, N2=4

        let fixture = writeFixture("duplicates.swift", content: code)
        let metrics = try calculator.calculate(for: fixture)

        XCTAssertEqual(metrics.n1, 2, "Distinct operators: let, =")
        XCTAssertEqual(metrics.N1, 4, "Total operators: let, =, let, =")
        XCTAssertEqual(metrics.n2, 3, "Distinct operands: x, 1, y")
        XCTAssertEqual(metrics.N2, 4, "Total operands: x, 1, y, x")
    }

    // TEST 4: Control flow keywords
    func test_controlFlow_keywordsCounted() throws {
        let code = """
        if true {
            let x = 1
        }
        """
        // Operators: if, let, =     → n1=3, N1=3
        // Operands: true, x, 1      → n2=3, N2=3

        let fixture = writeFixture("control.swift", content: code)
        let metrics = try calculator.calculate(for: fixture)

        XCTAssertEqual(metrics.n1, 3, "Distinct operators: if, let, =")
        XCTAssertEqual(metrics.n2, 3, "Distinct operands: true, x, 1")
    }

    // TEST 5: Arithmetic operators
    func test_arithmeticOperators_counted() throws {
        let code = """
        let x = 1 + 2
        """
        // Operators: let, =, +      → n1=3, N1=3
        // Operands: x, 1, 2         → n2=3, N2=3

        let fixture = writeFixture("arithmetic.swift", content: code)
        let metrics = try calculator.calculate(for: fixture)

        XCTAssertEqual(metrics.n1, 3, "Distinct operators: let, =, +")
        XCTAssertEqual(metrics.N1, 3, "Total operators")
        XCTAssertEqual(metrics.n2, 3, "Distinct operands: x, 1, 2")
    }
}
