import XCTest
@testable import SwiftHAL

final class RecommendationTests: XCTestCase {

    // MARK: - Recommendation Text Tests

    func test_recommendation_critical_risk_above_5() {
        var metrics = HalsteadMetrics(path: "test.swift")
        metrics.n1 = 100
        metrics.n2 = 200
        metrics.N1 = 1000
        metrics.N2 = 2000

        // Risk score will be volume/3000, we need > 5.0
        // So volume needs to be > 15000
        // volume = length * log2(vocab) = 3000 * log2(300) ≈ 24906

        let recommendation = recommendation(for: metrics)
        XCTAssertEqual(recommendation, "Critical - immediate refactoring needed")
    }

    func test_recommendation_high_risk_above_2() {
        var metrics = HalsteadMetrics(path: "test.swift")
        metrics.n1 = 50
        metrics.n2 = 100
        metrics.N1 = 400
        metrics.N2 = 800

        // volume = 1200 * log2(150) ≈ 8687, risk ≈ 2.9

        let recommendation = recommendation(for: metrics)
        XCTAssertEqual(recommendation, "High - review recommended")
    }

    func test_recommendation_moderate_risk_above_1() {
        var metrics = HalsteadMetrics(path: "test.swift")
        metrics.n1 = 30
        metrics.n2 = 50
        metrics.N1 = 200
        metrics.N2 = 300

        // volume = 500 * log2(80) ≈ 3161, risk ≈ 1.05

        let recommendation = recommendation(for: metrics)
        XCTAssertEqual(recommendation, "Moderate - monitor complexity")
    }

    func test_recommendation_low_risk_below_1_returns_nil() {
        var metrics = HalsteadMetrics(path: "test.swift")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100

        // volume = 150 * log2(30) ≈ 736, risk ≈ 0.25

        let recommendation = recommendation(for: metrics)
        XCTAssertNil(recommendation, "Files with risk < 1.0 should not appear in 'needs attention'")
    }

    // MARK: - Health Status Tests

    func test_health_status_good_below_1() {
        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 50
        totals.n2 = 100
        totals.N1 = 500
        totals.N2 = 1000

        // volume = 1500 * log2(150) ≈ 10859, risk ≈ 3.6
        // For 5 files: avgRisk = 3.6 / 5 = 0.72

        let status = getHealthStatus(totals: totals, fileCount: 5)
        XCTAssertEqual(status, "Good")
    }

    func test_health_status_fair_below_2() {
        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 50
        totals.n2 = 100
        totals.N1 = 800
        totals.N2 = 1600

        // volume = 2400 * log2(150) ≈ 17375, risk ≈ 5.8
        // For 5 files: avgRisk = 5.8 / 5 = 1.16

        let status = getHealthStatus(totals: totals, fileCount: 5)
        XCTAssertEqual(status, "Fair")
    }

    func test_health_status_needs_review_below_5() {
        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 80
        totals.n2 = 150
        totals.N1 = 1200
        totals.N2 = 2400

        // volume = 3600 * log2(230) ≈ 28226, risk ≈ 9.4
        // For 3 files: avgRisk = 9.4 / 3 = 3.13

        let status = getHealthStatus(totals: totals, fileCount: 3)
        XCTAssertEqual(status, "Needs Review")
    }

    func test_health_status_critical_above_5() {
        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 100
        totals.n2 = 200
        totals.N1 = 2000
        totals.N2 = 4000

        // volume = 6000 * log2(300) ≈ 49811, risk ≈ 16.6
        // For 3 files: avgRisk = 16.6 / 3 = 5.53

        let status = getHealthStatus(totals: totals, fileCount: 3)
        XCTAssertEqual(status, "Critical")
    }

    // MARK: - Filtering Tests

    func test_files_needing_attention_threshold_is_1() {
        let lowRisk = HalsteadMetrics(path: "low.swift")
        // risk = 0.66 (below threshold)

        var highRisk = HalsteadMetrics(path: "high.swift")
        highRisk.n1 = 50
        highRisk.n2 = 100
        highRisk.N1 = 400
        highRisk.N2 = 800
        // risk ≈ 2.9 (above threshold)

        let fileMetrics = [lowRisk, highRisk]
        let needsAttention = fileMetrics.filter { $0.riskScore >= 1.0 }

        XCTAssertEqual(needsAttention.count, 1)
        XCTAssertEqual(needsAttention.first?.path, "high.swift")
    }
}
