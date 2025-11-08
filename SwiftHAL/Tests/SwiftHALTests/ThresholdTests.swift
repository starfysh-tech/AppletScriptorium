import XCTest
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
    }

    func test_checkThreshold_passes() throws {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100
        // volume ≈ 735

        let threshold = try parseThreshold("volume>700")
        let violations = checkThresholds(metrics, thresholds: [threshold])

        XCTAssertTrue(violations.isEmpty, "Volume 735 > 700 should pass")
    }

    func test_checkThreshold_fails() throws {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100
        // volume ≈ 735

        let threshold = try parseThreshold("volume>800")
        let violations = checkThresholds(metrics, thresholds: [threshold])

        XCTAssertEqual(violations.count, 1, "Volume 735 > 800 should fail")
        XCTAssertTrue(violations[0].contains("volume"))
    }

    func test_checkMultipleThresholds() throws {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100

        let t1 = try parseThreshold("volume>800")  // Fails
        let t2 = try parseThreshold("difficulty<30")  // Passes (difficulty = 25)

        let violations = checkThresholds(metrics, thresholds: [t1, t2])

        XCTAssertEqual(violations.count, 1, "Only volume threshold should fail")
    }

    func test_checkThreshold_equal() throws {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20

        let threshold = try parseThreshold("vocabulary==30")
        let violations = checkThresholds(metrics, thresholds: [threshold])

        XCTAssertTrue(violations.isEmpty, "vocabulary 30 == 30 should pass")
    }
}
