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
    }

    func test_tableOutput_doesNotIncludeTotalsRow() {
        var metrics1 = HalsteadMetrics(path: "file1.swift")
        metrics1.n1 = 2
        metrics1.n2 = 2
        metrics1.N1 = 2
        metrics1.N2 = 2

        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 5
        totals.n2 = 5
        totals.N1 = 5
        totals.N2 = 5

        let table = formatAsTable([metrics1], totals: totals)

        XCTAssertFalse(table.contains("TOTALS"))
    }

    // SUMMARY OUTPUT TESTS

    func test_summaryOutput_onlyShowsHighRiskFiles() {
        // Create mix of high and low risk files
        // Risk = volume / 3000, so volume = risk * 3000
        let highRisk1 = createMetricsWithRisk(path: "high1.swift", targetRisk: 3.0)
        let highRisk2 = createMetricsWithRisk(path: "high2.swift", targetRisk: 2.5)
        let mediumRisk = createMetricsWithRisk(path: "medium.swift", targetRisk: 1.5)
        let lowRisk1 = createMetricsWithRisk(path: "low1.swift", targetRisk: 0.8)
        let lowRisk2 = createMetricsWithRisk(path: "low2.swift", targetRisk: 0.5)

        let allFiles = [highRisk1, highRisk2, mediumRisk, lowRisk1, lowRisk2]
        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 10
        totals.n2 = 20
        totals.N1 = 100
        totals.N2 = 200

        let summary = formatAsSummary(allFiles, totals: totals, verbose: false)

        // Files with risk >= 2.0 appear in "Files Needing Attention"
        XCTAssertTrue(summary.contains("high1.swift"))
        XCTAssertTrue(summary.contains("high2.swift"))

        // Medium/low-risk files (< 2.0) should NOT appear in "Files Needing Attention"
        let needsAttention = summary.components(separatedBy: "Files Needing Attention")[1].components(separatedBy: "Well-Factored Files")[0]
        XCTAssertFalse(needsAttention.contains("medium.swift"))  // 1.5 < 2.0
        XCTAssertFalse(needsAttention.contains("low1.swift"))  // 0.8 < 2.0
        XCTAssertFalse(needsAttention.contains("low2.swift"))  // 0.5 < 2.0
    }

    func test_summaryOutput_countsOnlyHighRiskFiles() {
        let highRisk1 = createMetricsWithRisk(path: "high1.swift", targetRisk: 3.0)
        let highRisk2 = createMetricsWithRisk(path: "high2.swift", targetRisk: 2.5)
        let mediumRisk = createMetricsWithRisk(path: "medium.swift", targetRisk: 1.5)
        let lowRisk = createMetricsWithRisk(path: "low.swift", targetRisk: 0.8)

        let allFiles = [highRisk1, highRisk2, mediumRisk, lowRisk]
        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 10
        totals.n2 = 20
        totals.N1 = 100
        totals.N2 = 200

        let summary = formatAsSummary(allFiles, totals: totals, verbose: false)

        // Header should say "3 files need attention" (high1=3.0, high2=2.5, medium=1.5 all >= 1.0 threshold)
        XCTAssertTrue(summary.contains("3 files need attention"))
        XCTAssertFalse(summary.contains("4 files need attention"))
    }

    func test_summaryOutput_usesCorrectGrammar() {
        // Test singular - 1 file with risk >= 2.0, rest below threshold
        let highRisk = createMetricsWithRisk(path: "high.swift", targetRisk: 3.0)
        let lowRisk = createMetricsWithRisk(path: "low.swift", targetRisk: 0.5)

        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 10
        totals.n2 = 20
        totals.N1 = 100
        totals.N2 = 200

        let summarySingular = formatAsSummary([highRisk, lowRisk], totals: totals, verbose: false)
        XCTAssertTrue(summarySingular.contains("1 file needs attention"))

        // Test plural - 2 files with risk >= 1.0
        let highRisk2 = createMetricsWithRisk(path: "high2.swift", targetRisk: 2.5)
        let summaryPlural = formatAsSummary([highRisk, highRisk2, lowRisk], totals: totals, verbose: false)
        XCTAssertTrue(summaryPlural.contains("2 files need attention"))
    }

    func test_summaryOutput_showsFewerThanFiveIfNotEnoughHighRisk() {
        // Create 4 files with risk >= 1.0, and 1 file with risk < 1.0
        let high1 = createMetricsWithRisk(path: "high1.swift", targetRisk: 4.0)
        let high2 = createMetricsWithRisk(path: "high2.swift", targetRisk: 3.0)
        let high3 = createMetricsWithRisk(path: "high3.swift", targetRisk: 2.1)
        let medium = createMetricsWithRisk(path: "medium.swift", targetRisk: 1.5)
        let low = createMetricsWithRisk(path: "low.swift", targetRisk: 0.5)

        let allFiles = [high1, high2, high3, medium, low]
        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 10
        totals.n2 = 20
        totals.N1 = 100
        totals.N2 = 200

        let summary = formatAsSummary(allFiles, totals: totals, verbose: false)

        // Should show 4 files with risk >= 1.0 (high1=4.0, high2=3.0, high3=2.1, medium=1.5)
        XCTAssertTrue(summary.contains("4 files need attention"))
        XCTAssertTrue(summary.contains("high1.swift"))
        XCTAssertTrue(summary.contains("high2.swift"))
        XCTAssertTrue(summary.contains("high3.swift"))
        XCTAssertTrue(summary.contains("medium.swift"))  // 1.5 >= 1.0 threshold

        // Low-risk file should not appear in "Files Needing Attention"
        let needsAttention = summary.components(separatedBy: "Files Needing Attention")[1].components(separatedBy: "Well-Factored Files")[0]
        XCTAssertFalse(needsAttention.contains("low.swift"))  // 0.5 < 1.0
    }

    // RISK DISTRIBUTION TESTS

    func test_riskDistribution_categorizesFilesCorrectly() {
        let critical1 = createMetricsWithRisk(path: "critical1.swift", targetRisk: 7.8)
        let high1 = createMetricsWithRisk(path: "high1.swift", targetRisk: 4.0)
        let high2 = createMetricsWithRisk(path: "high2.swift", targetRisk: 3.0)
        let high3 = createMetricsWithRisk(path: "high3.swift", targetRisk: 2.5)
        let high4 = createMetricsWithRisk(path: "high4.swift", targetRisk: 2.0)
        let moderate1 = createMetricsWithRisk(path: "mod1.swift", targetRisk: 1.8)
        let low1 = createMetricsWithRisk(path: "low1.swift", targetRisk: 0.8)

        let allFiles = [critical1, high1, high2, high3, high4, moderate1, low1]
        let distribution = formatRiskDistribution(allFiles)

        // Should show counts for each category
        XCTAssertTrue(distribution.contains("Critical (≥5.0)"))
        XCTAssertTrue(distribution.contains("High (2.0-5.0)"))
        XCTAssertTrue(distribution.contains("Moderate (1.0-2.0)"))
        XCTAssertTrue(distribution.contains("Low (<1.0)"))

        // Should show correct counts (percentages may vary due to rounding)
        XCTAssertTrue(distribution.contains("🔴"))
        XCTAssertTrue(distribution.contains("🟡"))
        XCTAssertTrue(distribution.contains("🟠"))
        XCTAssertTrue(distribution.contains("🟢"))
    }

    func test_riskDistribution_showsFocusCount() {
        let critical1 = createMetricsWithRisk(path: "critical1.swift", targetRisk: 6.0)
        let high1 = createMetricsWithRisk(path: "high1.swift", targetRisk: 3.0)
        let high2 = createMetricsWithRisk(path: "high2.swift", targetRisk: 2.5)
        let moderate1 = createMetricsWithRisk(path: "mod1.swift", targetRisk: 1.5)

        let allFiles = [critical1, high1, high2, moderate1]
        let distribution = formatRiskDistribution(allFiles)

        // Focus count = critical + high = 1 + 2 = 3
        XCTAssertTrue(distribution.contains("Focus: 3 files"))
    }

    func test_riskDistribution_usesFixedWidthBars() {
        let critical1 = createMetricsWithRisk(path: "critical1.swift", targetRisk: 6.0)
        let low1 = createMetricsWithRisk(path: "low1.swift", targetRisk: 0.5)

        let allFiles = [critical1, low1]
        let distribution = formatRiskDistribution(allFiles)

        // Each bar should have consistent width regardless of count
        // Critical (1 file) and Low (1 file) should have same bar length
        let lines = distribution.components(separatedBy: "\n")
        let criticalLine = lines.first { $0.contains("Critical") } ?? ""
        let lowLine = lines.first { $0.contains("Low") } ?? ""

        // Count block characters (▓) in each line
        let criticalBlocks = criticalLine.filter { $0 == "▓" }.count
        let lowBlocks = lowLine.filter { $0 == "▓" }.count

        // Both should have at least 1 block, same count since both have 1 file
        XCTAssertGreaterThan(criticalBlocks, 0)
        XCTAssertGreaterThan(lowBlocks, 0)
        XCTAssertEqual(criticalBlocks, lowBlocks)
    }

    func test_riskDistribution_barsProportionalToPercentage() {
        // Create distribution: 1% critical, 7% high, 19% moderate, 73% low
        // Total: 100 files
        let criticalFiles = (0..<1).map { createMetricsWithRisk(path: "critical\($0).swift", targetRisk: 6.0) }
        let highFiles = (0..<7).map { createMetricsWithRisk(path: "high\($0).swift", targetRisk: 3.0) }
        let moderateFiles = (0..<19).map { createMetricsWithRisk(path: "mod\($0).swift", targetRisk: 1.5) }
        let lowFiles = (0..<73).map { createMetricsWithRisk(path: "low\($0).swift", targetRisk: 0.5) }

        let allFiles = criticalFiles + highFiles + moderateFiles + lowFiles
        let distribution = formatRiskDistribution(allFiles)

        let lines = distribution.components(separatedBy: "\n")
        let criticalLine = lines.first { $0.contains("Critical") } ?? ""
        let highLine = lines.first { $0.contains("High") } ?? ""
        let moderateLine = lines.first { $0.contains("Moderate") } ?? ""
        let lowLine = lines.first { $0.contains("Low") } ?? ""

        // Count block characters (▓) - bars should be proportional to PERCENTAGE not file count
        let criticalBlocks = criticalLine.filter { $0 == "▓" }.count
        let highBlocks = highLine.filter { $0 == "▓" }.count
        let moderateBlocks = moderateLine.filter { $0 == "▓" }.count
        let lowBlocks = lowLine.filter { $0 == "▓" }.count

        // With 50-char bar width and rounding:
        // 1/100 = 1% → 1 block (1 * 50 / 100 = 0.5 → round to 1, then max with 1)
        // 7/100 = 7% → 4 blocks (7 * 50 / 100 = 3.5 → round to 4)
        // 19/100 = 19% → 10 blocks (19 * 50 / 100 = 9.5 → round to 10)
        // 73/100 = 73% → 37 blocks (73 * 50 / 100 = 36.5 → round to 37)
        XCTAssertEqual(criticalBlocks, 1, "1% should show 1 block")
        XCTAssertEqual(highBlocks, 4, "7% should show 4 blocks")
        XCTAssertEqual(moderateBlocks, 10, "19% should show 10 blocks")
        XCTAssertEqual(lowBlocks, 37, "73% should show 37 blocks")

        // Bars should be proportional to percentages (not file counts)
        // Low (37 blocks) should be ~9× longer than High (4 blocks)
        let ratio = Double(lowBlocks) / Double(highBlocks)
        XCTAssertGreaterThan(ratio, 8.0, "Low bar should be much longer than High bar")
        XCTAssertLessThan(ratio, 11.0, "But not absurdly longer")
    }

    func test_criticalSection_showsAllCriticalAndHighFiles() {
        let critical1 = createMetricsWithRisk(path: "App/ContactRippleApp.swift", targetRisk: 7.8)
        let critical2 = createMetricsWithRisk(path: "App/CriticalTwo.swift", targetRisk: 5.5)
        let high1 = createMetricsWithRisk(path: "Feature/HighOne.swift", targetRisk: 4.0)
        let high2 = createMetricsWithRisk(path: "Feature/HighTwo.swift", targetRisk: 3.0)
        let high3 = createMetricsWithRisk(path: "Feature/HighThree.swift", targetRisk: 2.5)
        let high4 = createMetricsWithRisk(path: "Feature/HighFour.swift", targetRisk: 2.1)
        let moderate1 = createMetricsWithRisk(path: "Utils/Moderate.swift", targetRisk: 1.5)
        let low1 = createMetricsWithRisk(path: "Utils/Low.swift", targetRisk: 0.5)

        let allFiles = [critical1, critical2, high1, high2, high3, high4, moderate1, low1]
        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 10
        totals.n2 = 20
        totals.N1 = 100
        totals.N2 = 200

        let summary = formatAsSummary(allFiles, totals: totals, verbose: false)

        // Should show ALL critical and high files (6 total), not just top 5
        XCTAssertTrue(summary.contains("ContactRippleApp.swift"))
        XCTAssertTrue(summary.contains("CriticalTwo.swift"))
        XCTAssertTrue(summary.contains("HighOne.swift"))
        XCTAssertTrue(summary.contains("HighTwo.swift"))
        XCTAssertTrue(summary.contains("HighThree.swift"))
        XCTAssertTrue(summary.contains("HighFour.swift"))

        // Extract just the "Files Needing Attention" section
        if let startRange = summary.range(of: "⚠️  Files Needing Attention"),
           let endRange = summary.range(of: "✓  Well-Factored Files") {
            let criticalSection = String(summary[startRange.upperBound..<endRange.lowerBound])
            // Moderate and Low should NOT appear in critical section (only risk >= 2.0)
            XCTAssertFalse(criticalSection.contains("Moderate.swift"))
            XCTAssertFalse(criticalSection.contains("Low.swift"))
        } else {
            XCTFail("Could not find 'Files Needing Attention' or 'Well-Factored Files' sections")
        }
    }

    func test_criticalSection_showsProjectAvgComparison() {
        let critical1 = createMetricsWithRisk(path: "App/ContactRippleApp.swift", targetRisk: 7.8)
        let low1 = createMetricsWithRisk(path: "Utils/Low.swift", targetRisk: 0.5)

        let allFiles = [critical1, low1]
        var totals = HalsteadMetrics(path: "TOTALS")
        totals.n1 = 10
        totals.n2 = 20
        totals.N1 = 100
        totals.N2 = 200

        let summary = formatAsSummary(allFiles, totals: totals, verbose: false)

        // Should show comparison to project average
        XCTAssertTrue(summary.contains("× project avg"))
        // Should show compact one-line format with Risk, Vol, Diff, and comparison
        XCTAssertTrue(summary.contains("Risk:"))
        XCTAssertTrue(summary.contains("Vol:"))
        XCTAssertTrue(summary.contains("Diff:"))
        // Should NOT contain progress bar characters
        XCTAssertFalse(summary.contains("████████████████████████████"))
    }

    // Helper to create metrics with specific risk score
    private func createMetricsWithRisk(path: String, targetRisk: Double) -> HalsteadMetrics {
        var metrics = HalsteadMetrics(path: path)
        // Risk = volume / 3000
        // Volume = length * log2(vocabulary)
        // For vocab=30: log2(30) ≈ 4.9
        // We need: length * 4.9 = targetRisk * 3000
        // So: length = targetRisk * 3000 / 4.9 ≈ targetRisk * 612
        metrics.n1 = 10
        metrics.n2 = 20
        let targetLength = Int(targetRisk * 612)
        metrics.N1 = targetLength / 3
        metrics.N2 = (targetLength * 2) / 3
        return metrics
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
