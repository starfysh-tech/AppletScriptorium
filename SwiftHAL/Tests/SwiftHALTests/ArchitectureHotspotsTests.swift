import XCTest
@testable import SwiftHAL

final class ArchitectureHotspotsTests: XCTestCase {

    // MARK: - groupByDirectory tests

    func test_groupByDirectory_extracts_top_level_only() {
        var metrics1 = HalsteadMetrics(path: "App/Views/File.swift")
        metrics1.n1 = 10
        metrics1.n2 = 20
        metrics1.N1 = 50
        metrics1.N2 = 100

        var metrics2 = HalsteadMetrics(path: "App/Models/User.swift")
        metrics2.n1 = 5
        metrics2.n2 = 10
        metrics2.N1 = 25
        metrics2.N2 = 50

        var metrics3 = HalsteadMetrics(path: "SwiftUI/Components/Button.swift")
        metrics3.n1 = 3
        metrics3.n2 = 6
        metrics3.N1 = 15
        metrics3.N2 = 30

        let grouped = groupByDirectory([metrics1, metrics2, metrics3])

        XCTAssertEqual(grouped.count, 2)
        XCTAssertTrue(grouped.keys.contains("App/"))
        XCTAssertTrue(grouped.keys.contains("SwiftUI/"))
        XCTAssertEqual(grouped["App/"]?.count, 2)
        XCTAssertEqual(grouped["SwiftUI/"]?.count, 1)
    }

    func test_groupByDirectory_handles_root_level_files() {
        var metrics = HalsteadMetrics(path: "main.swift")
        metrics.n1 = 10
        metrics.n2 = 20
        metrics.N1 = 50
        metrics.N2 = 100

        let grouped = groupByDirectory([metrics])

        XCTAssertEqual(grouped.count, 1)
        XCTAssertTrue(grouped.keys.contains("."))
        XCTAssertEqual(grouped["."]?.count, 1)
    }

    func test_groupByDirectory_aggregates_all_subdirectories() {
        var metrics1 = HalsteadMetrics(path: "App/Views/Home/HomeView.swift")
        metrics1.n1 = 10
        metrics1.n2 = 20
        metrics1.N1 = 50
        metrics1.N2 = 100

        var metrics2 = HalsteadMetrics(path: "App/Views/Settings/SettingsView.swift")
        metrics2.n1 = 5
        metrics2.n2 = 10
        metrics2.N1 = 25
        metrics2.N2 = 50

        var metrics3 = HalsteadMetrics(path: "App/Models/User.swift")
        metrics3.n1 = 3
        metrics3.n2 = 6
        metrics3.N1 = 15
        metrics3.N2 = 30

        let grouped = groupByDirectory([metrics1, metrics2, metrics3])

        XCTAssertEqual(grouped.count, 1)
        XCTAssertTrue(grouped.keys.contains("App/"))
        XCTAssertEqual(grouped["App/"]?.count, 3)
    }

    // MARK: - DirectoryStats tests

    func test_directory_stats_calculates_average_risk() {
        var metrics1 = HalsteadMetrics(path: "App/File1.swift")
        metrics1.n1 = 10
        metrics1.n2 = 20
        metrics1.N1 = 200  // Higher volume = higher risk
        metrics1.N2 = 400

        var metrics2 = HalsteadMetrics(path: "App/File2.swift")
        metrics2.n1 = 5
        metrics2.n2 = 10
        metrics2.N1 = 100
        metrics2.N2 = 200

        let stats = DirectoryStats(files: [metrics1, metrics2])

        XCTAssertEqual(stats.file_count, 2)
        XCTAssertGreaterThan(stats.avg_risk, 0.0)
        XCTAssertEqual(stats.avg_risk, (metrics1.riskScore + metrics2.riskScore) / 2.0)
    }

    func test_directory_stats_counts_priority_files() {
        // Create files with different risk levels
        // Risk = volume / 3000
        // Volume = length * log2(vocabulary)

        var critical = HalsteadMetrics(path: "App/Critical.swift")
        critical.n1 = 10
        critical.n2 = 20
        critical.N1 = 3000  // Risk ≈ 5.0
        critical.N2 = 6000

        var high = HalsteadMetrics(path: "App/High.swift")
        high.n1 = 10
        high.n2 = 20
        high.N1 = 1000  // Risk ≈ 2.0
        high.N2 = 2000

        var moderate = HalsteadMetrics(path: "App/Moderate.swift")
        moderate.n1 = 10
        moderate.n2 = 20
        moderate.N1 = 300  // Risk ≈ 1.0
        moderate.N2 = 600

        var low = HalsteadMetrics(path: "App/Low.swift")
        low.n1 = 5
        low.n2 = 10
        low.N1 = 50  // Risk < 1.0
        low.N2 = 100

        let stats = DirectoryStats(files: [critical, high, moderate, low])

        XCTAssertEqual(stats.file_count, 4)
        XCTAssertEqual(stats.critical_count, 1)  // risk >= 5.0
        XCTAssertEqual(stats.high_count, 1)      // 2.0 <= risk < 5.0
        XCTAssertEqual(stats.moderate_count, 1)  // 1.0 <= risk < 2.0
        XCTAssertEqual(stats.low_count, 1)       // risk < 1.0
    }

    // MARK: - formatArchitectureHotspots tests

    func test_formatArchitectureHotspots_shows_all_directories() {
        var critical = HalsteadMetrics(path: "App/Critical.swift")
        critical.n1 = 10
        critical.n2 = 20
        critical.N1 = 3000
        critical.N2 = 6000

        var high = HalsteadMetrics(path: "SwiftUI/High.swift")
        high.n1 = 10
        high.n2 = 20
        high.N1 = 1000
        high.N2 = 2000

        var low = HalsteadMetrics(path: "Services/Low.swift")
        low.n1 = 5
        low.n2 = 10
        low.N1 = 50
        low.N2 = 100

        let output = formatArchitectureHotspots([critical, high, low])

        XCTAssertTrue(output.contains("ARCHITECTURE HOTSPOTS"))
        XCTAssertTrue(output.contains("App/"))
        XCTAssertTrue(output.contains("SwiftUI/"))
        XCTAssertTrue(output.contains("Services/"))
    }

    func test_formatArchitectureHotspots_sorts_by_priority() {
        var critical = HalsteadMetrics(path: "Critical/File.swift")
        critical.n1 = 10
        critical.n2 = 20
        critical.N1 = 3000
        critical.N2 = 6000

        var high = HalsteadMetrics(path: "High/File.swift")
        high.n1 = 10
        high.n2 = 20
        high.N1 = 1000
        high.N2 = 2000

        var moderate = HalsteadMetrics(path: "Moderate/File.swift")
        moderate.n1 = 10
        moderate.n2 = 20
        moderate.N1 = 300
        moderate.N2 = 600

        var low = HalsteadMetrics(path: "Low/File.swift")
        low.n1 = 5
        low.n2 = 10
        low.N1 = 50
        low.N2 = 100

        let output = formatArchitectureHotspots([critical, high, moderate, low])
        let lines = output.split(separator: "\n").map(String.init)

        // Find directory lines (those starting with 📁)
        let directoryLines = lines.filter { $0.contains("📁") }

        // Critical should come first, then high, moderate, low
        let criticalIndex = directoryLines.firstIndex { $0.contains("Critical/") } ?? -1
        let highIndex = directoryLines.firstIndex { $0.contains("High/") } ?? -1
        let moderateIndex = directoryLines.firstIndex { $0.contains("Moderate/") } ?? -1
        let lowIndex = directoryLines.firstIndex { $0.contains("Low/") } ?? -1

        XCTAssertLessThan(criticalIndex, highIndex)
        XCTAssertLessThan(highIndex, moderateIndex)
        XCTAssertLessThan(moderateIndex, lowIndex)
    }

    func test_formatArchitectureHotspots_shows_priority_indicators() {
        var critical = HalsteadMetrics(path: "Critical/File.swift")
        critical.n1 = 10
        critical.n2 = 20
        critical.N1 = 3000
        critical.N2 = 6000

        var high = HalsteadMetrics(path: "High/File.swift")
        high.n1 = 10
        high.n2 = 20
        high.N1 = 1000
        high.N2 = 2000

        var low = HalsteadMetrics(path: "Low/File.swift")
        low.n1 = 5
        low.n2 = 10
        low.N1 = 50
        low.N2 = 100

        let output = formatArchitectureHotspots([critical, high, low])

        // Check for emojis
        XCTAssertTrue(output.contains("🔴"))  // Critical
        XCTAssertTrue(output.contains("🟡"))  // High
        XCTAssertTrue(output.contains("🟢"))  // Low/Clean
    }

    func test_formatArchitectureHotspots_displays_average_risk() {
        var file1 = HalsteadMetrics(path: "App/File1.swift")
        file1.n1 = 10
        file1.n2 = 20
        file1.N1 = 1000
        file1.N2 = 2000

        var file2 = HalsteadMetrics(path: "App/File2.swift")
        file2.n1 = 10
        file2.n2 = 20
        file2.N1 = 1000
        file2.N2 = 2000

        let output = formatArchitectureHotspots([file1, file2])
        let avgRisk = (file1.riskScore + file2.riskScore) / 2.0

        // Output should contain the average risk rounded to 2 decimal places
        let avgRiskStr = String(format: "%.2f", avgRisk)
        XCTAssertTrue(output.contains(avgRiskStr))
    }

    func test_formatArchitectureHotspots_shows_clean_for_low_risk() {
        var low1 = HalsteadMetrics(path: "Services/Low1.swift")
        low1.n1 = 5
        low1.n2 = 10
        low1.N1 = 50
        low1.N2 = 100

        var low2 = HalsteadMetrics(path: "Services/Low2.swift")
        low2.n1 = 5
        low2.n2 = 10
        low2.N1 = 50
        low2.N2 = 100

        var low3 = HalsteadMetrics(path: "Services/Low3.swift")
        low3.n1 = 5
        low3.n2 = 10
        low3.N1 = 50
        low3.N2 = 100

        let output = formatArchitectureHotspots([low1, low2, low3])

        XCTAssertTrue(output.contains("Clean (3 files)"))
    }
}
