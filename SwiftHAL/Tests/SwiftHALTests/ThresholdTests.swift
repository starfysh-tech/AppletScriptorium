import XCTest
import ArgumentParser
@testable import SwiftHAL

final class ThresholdTests: XCTestCase {

    func test_parseThreshold_greaterThan() throws {
        let threshold = try parseThreshold("volume>800")

        XCTAssertEqual(threshold.metric, "volume")
        XCTAssertEqual(threshold.comparator, .greaterThan)
        XCTAssertEqual(threshold.value, 800.0)
    }

    func test_parseThreshold_greaterThanOrEqual() throws {
        let threshold = try parseThreshold("difficulty>=20")

        XCTAssertEqual(threshold.comparator, .greaterThanOrEqual)
    }

    func test_parseThreshold_lessThan() throws {
        let threshold = try parseThreshold("riskScore<1")

        XCTAssertEqual(threshold.comparator, .lessThan)
        XCTAssertEqual(getMetricValue(HalsteadMetrics(path: "t"), metric: "riskScore"), 0.0)
    }

    func test_parseThreshold_unknownMetric_throws() {
        XCTAssertThrowsError(try parseThreshold("volum>800"))
    }

    func test_checkThreshold_underLimit_passes() throws {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100
        // volume ≈ 735

        let threshold = try parseThreshold("volume>800")
        let violations = checkThresholds(metrics, thresholds: [threshold])

        XCTAssertTrue(violations.isEmpty, "volume>800 fails only when volume is over 800; 735 passes")
    }

    func test_checkThreshold_overLimit_fails() throws {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100
        // volume ≈ 735

        let threshold = try parseThreshold("volume>700")
        let violations = checkThresholds(metrics, thresholds: [threshold])

        XCTAssertEqual(violations.count, 1, "volume>700 fails when volume is 735")
        XCTAssertTrue(violations[0].contains("volume"))
    }

    func test_checkMultipleThresholds() throws {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100

        let t1 = try parseThreshold("volume>700")  // Fails (volume ≈ 735)
        let t2 = try parseThreshold("difficulty>30")  // Passes (difficulty = 25)

        let violations = checkThresholds(metrics, thresholds: [t1, t2])

        XCTAssertEqual(violations.count, 1, "Only volume threshold should fail")
    }

    func test_checkThreshold_equal_failsOnMatch() throws {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20

        let threshold = try parseThreshold("vocabulary==30")
        let violations = checkThresholds(metrics, thresholds: [threshold])

        XCTAssertEqual(violations.count, 1, "vocabulary==30 fails when vocabulary is 30")
    }

    // MARK: - runAnalysis exit codes

    private var tempDir: URL!

    override func setUp() {
        super.setUp()
        tempDir = FileManager.default.temporaryDirectory.appendingPathComponent("SwiftHALThresholds-\(UUID().uuidString)")
        try! FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
    }

    override func tearDown() {
        try? FileManager.default.removeItem(at: tempDir)
        super.tearDown()
    }

    private func analyze(threshold: String) throws {
        var options = CLIOptions()
        options.path = tempDir.path
        options.format = .json
        options.output_path = tempDir.appendingPathComponent("out.json").path
        options.thresholds = [threshold]
        try SwiftHAL.runAnalysis(options: options)
    }

    func test_runAnalysis_exits2_whenFileExceedsThreshold() throws {
        try "let a = 1".write(to: tempDir.appendingPathComponent("a.swift"), atomically: true, encoding: .utf8)

        XCTAssertThrowsError(try analyze(threshold: "volume>1")) { error in
            XCTAssertEqual(error as? ExitCode, ExitCode(2))
        }
        XCTAssertNoThrow(try analyze(threshold: "volume>100000"))
    }

    func test_runAnalysis_ignoresProjectTotals() throws {
        try "let a = 1 + 2".write(to: tempDir.appendingPathComponent("a.swift"), atomically: true, encoding: .utf8)
        try "var b = 3 - 4".write(to: tempDir.appendingPathComponent("b.swift"), atomically: true, encoding: .utf8)

        let calculator = MetricsCalculator()
        let results = try ["a.swift", "b.swift"].map { try calculator.calculateWithSets(for: tempDir.appendingPathComponent($0)) }
        let maxFileVolume = results.map { $0.metrics.volume }.max()!
        let totalsVolume = aggregateTotals(results).volume
        XCTAssertGreaterThan(totalsVolume, maxFileVolume)

        // Between the largest file and the totals: only a totals check would fail
        let limit = (maxFileVolume + totalsVolume) / 2
        XCTAssertNoThrow(try analyze(threshold: "volume>\(limit)"))
    }
}
