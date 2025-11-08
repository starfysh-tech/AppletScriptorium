import XCTest
@testable import SwiftHAL

final class FormulaTests: XCTestCase {

    func test_vocabulary_sumsDistinctCounts() {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20

        XCTAssertEqual(metrics.vocabulary, 30, "vocabulary = n1 + n2")
    }

    func test_length_sumsTotalCounts() {
        var metrics = HalsteadMetrics(path: "test")
        metrics.N1 = 50
        metrics.N2 = 100

        XCTAssertEqual(metrics.length, 150, "length = N1 + N2")
    }

    func test_estimatedLength_followsHalsteadFormula() {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20

        // N_hat = n1 * log2(n1) + n2 * log2(n2)
        let expected = 10.0 * log2(10.0) + 20.0 * log2(20.0)

        XCTAssertEqual(metrics.estimatedLength, expected, accuracy: 0.01)
    }

    func test_volume_followsHalsteadFormula() {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100

        // V = N * log2(n)
        let expected = 150.0 * log2(30.0)

        XCTAssertEqual(metrics.volume, expected, accuracy: 0.01)
    }

    func test_difficulty_followsHalsteadFormula() {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100

        // D = (n1 / 2) * (N2 / n2)
        let expected = (10.0 / 2.0) * (100.0 / 20.0)

        XCTAssertEqual(metrics.difficulty, expected, accuracy: 0.01)
    }

    func test_effort_followsHalsteadFormula() {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100

        // E = D * V
        let expected = metrics.difficulty * metrics.volume

        XCTAssertEqual(metrics.effort, expected, accuracy: 0.01)
    }

    func test_time_followsHalsteadFormula() {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100

        // T = E / 18
        let expected = metrics.effort / 18.0

        XCTAssertEqual(metrics.timeSeconds, expected, accuracy: 0.01)
    }

    func test_riskScore_followsStandardFormula() {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100

        // riskScore = V / 3000 (from spec)
        let expected = metrics.volume / 3000.0

        XCTAssertEqual(metrics.riskScore, expected, accuracy: 0.0001)
    }

    // EDGE CASES

    func test_emptyMetrics_producesZeroVolume() {
        let metrics = HalsteadMetrics(path: "test")
        // All defaults to 0

        XCTAssertEqual(metrics.volume, 0.0, "Zero length/vocabulary → zero volume")
    }

    func test_zeroN2_producesZeroDifficulty() {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        metrics.N1 = 20
        // n2 = 0, N2 = 0

        XCTAssertEqual(metrics.difficulty, 0.0, "n2=0 → guard against divide-by-zero")
    }

    func test_zeroN1OrN2_producesZeroEstimatedLength() {
        var metrics = HalsteadMetrics(path: "test")
        metrics.n1 = 10
        // n2 = 0

        XCTAssertEqual(metrics.estimatedLength, 0.0, "n2=0 → cannot compute log2")
    }
}
