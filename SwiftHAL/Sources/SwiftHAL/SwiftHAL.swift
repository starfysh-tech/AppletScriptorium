import Foundation
import SwiftSyntax
import SwiftParser
import ArgumentParser

// MARK: - Data Structures

struct HalsteadMetrics: Codable {
    let path: String

    // Raw counts
    var n1: Int = 0 // Distinct operators
    var n2: Int = 0 // Distinct operands
    var N1: Int = 0 // Total operators
    var N2: Int = 0 // Total operands

    // Calculated metrics
    var vocabulary: Int { n1 + n2 }
    var length: Int { N1 + N2 }
    var estimatedLength: Double {
        guard n1 > 0 && n2 > 0 else { return 0 }
        return Double(n1) * log2(Double(n1)) + Double(n2) * log2(Double(n2))
    }
    var volume: Double {
        guard length > 0 && vocabulary > 0 else { return 0 }
        return Double(length) * log2(Double(vocabulary))
    }
    var difficulty: Double {
        guard n2 > 0 && N2 > 0 else { return 0 }
        return (Double(n1) / 2.0) * (Double(N2) / Double(n2))
    }
    var effort: Double { difficulty * volume }
    var timeSeconds: Double { effort / 18.0 }
    // Predicted defect density (NOT actual bugs)
    var riskScore: Double { volume / 3000.0 }

    init(path: String) {
        self.path = path
    }

    // Custom encoding to include computed properties
    enum CodingKeys: String, CodingKey {
        case path, n1, n2, N1, N2
        case vocabulary, length, estimatedLength, volume, difficulty, effort, timeSeconds, riskScore
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(path, forKey: .path)
        try container.encode(n1, forKey: .n1)
        try container.encode(n2, forKey: .n2)
        try container.encode(N1, forKey: .N1)
        try container.encode(N2, forKey: .N2)
        try container.encode(vocabulary, forKey: .vocabulary)
        try container.encode(length, forKey: .length)
        try container.encode(estimatedLength, forKey: .estimatedLength)
        try container.encode(volume, forKey: .volume)
        try container.encode(difficulty, forKey: .difficulty)
        try container.encode(effort, forKey: .effort)
        try container.encode(timeSeconds, forKey: .timeSeconds)
        try container.encode(riskScore, forKey: .riskScore)
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        path = try container.decode(String.self, forKey: .path)
        n1 = try container.decode(Int.self, forKey: .n1)
        n2 = try container.decode(Int.self, forKey: .n2)
        N1 = try container.decode(Int.self, forKey: .N1)
        N2 = try container.decode(Int.self, forKey: .N2)
        // Computed properties are automatically calculated from stored properties
    }
}

// MARK: - Metric Access

enum MetricKey: String, CaseIterable {
    case n1, n2, vocabulary, length, volume, difficulty, effort, time, riskScore, estimatedLength

    var keyPath: KeyPath<HalsteadMetrics, Double> {
        switch self {
        case .n1: return \.n1AsDouble
        case .n2: return \.n2AsDouble
        case .vocabulary: return \.vocabularyAsDouble
        case .length: return \.lengthAsDouble
        case .volume: return \.volume
        case .difficulty: return \.difficulty
        case .effort: return \.effort
        case .time: return \.timeSeconds
        case .riskScore: return \.riskScore
        case .estimatedLength: return \.estimatedLength
        }
    }

    init?(string: String) {
        let normalized = string.lowercased()
        if let key = MetricKey(rawValue: normalized) {
            self = key
        } else if normalized == "n" {
            self = .vocabulary
        } else if normalized == "timeseconds" {
            self = .time
        } else {
            return nil
        }
    }
}

extension HalsteadMetrics {
    var n1AsDouble: Double { Double(n1) }
    var n2AsDouble: Double { Double(n2) }
    var vocabularyAsDouble: Double { Double(vocabulary) }
    var lengthAsDouble: Double { Double(length) }
}

// MARK: - Token Classification

enum HalsteadToken {
    case `operator`
    case operand
    case ignored
}

struct TokenClassifier {
    static func classify(_ token: TokenSyntax) -> HalsteadToken {
        switch token.tokenKind {

        // MARK: Operators

        // Associated value operators
        case .binaryOperator(_), .prefixOperator(_), .postfixOperator(_):
            return .operator

        // Punctuation operators
        case .equal, .colon, .comma, .arrow, .exclamationMark, .infixQuestionMark,
             .postfixQuestionMark, .period, .ellipsis, .leftAngle, .rightAngle,
             .semicolon, .prefixAmpersand, .wildcard:
            return .operator

        // Control flow keywords
        case .keyword(.if), .keyword(.else), .keyword(.for), .keyword(.while),
             .keyword(.repeat), .keyword(.switch), .keyword(.case), .keyword(.default),
             .keyword(.guard):
            return .operator

        // Declaration keywords
        case .keyword(.func), .keyword(.class), .keyword(.struct), .keyword(.enum),
             .keyword(.protocol):
            return .operator

        // Other operator keywords
        case .keyword(.import), .keyword(.let), .keyword(.var), .keyword(.in),
             .keyword(.return), .keyword(.break), .keyword(.continue), .keyword(.defer),
             .keyword(.throw), .keyword(.throws), .keyword(.rethrows), .keyword(.try),
             .keyword(.do), .keyword(.catch), .keyword(.where), .keyword(.as), .keyword(.is):
            return .operator

        // MARK: Operands

        // Identifiers
        case .identifier(_), .dollarIdentifier(_):
            return .operand

        // Literals
        case .integerLiteral(_), .floatLiteral(_), .stringSegment(_), .regexLiteralPattern(_):
            return .operand

        // Literal keywords
        case .keyword(.true), .keyword(.false), .keyword(.nil):
            return .operand

        // MARK: Ignored
        default:
            return .ignored
        }
    }
}

// MARK: - Metrics Calculation

struct MetricsWithSets {
    let metrics: HalsteadMetrics
    let operators: Set<String>
    let operands: Set<String>
}

class MetricsCalculator {
    func calculate(for fileURL: URL) throws -> HalsteadMetrics {
        let result = try calculateWithSets(for: fileURL)
        return result.metrics
    }

    func calculateWithSets(for fileURL: URL) throws -> MetricsWithSets {
        let source = try String(contentsOf: fileURL, encoding: .utf8)
        let tree = Parser.parse(source: source)

        var metrics = HalsteadMetrics(path: fileURL.path)
        var distinctOperators = Set<String>()
        var distinctOperands = Set<String>()

        for token in tree.tokens(viewMode: .sourceAccurate) {
            let classification = TokenClassifier.classify(token)
            let tokenText = token.text

            switch classification {
            case .operator:
                metrics.N1 += 1
                distinctOperators.insert(tokenText)
            case .operand:
                metrics.N2 += 1
                distinctOperands.insert(tokenText)
            case .ignored:
                continue
            }
        }

        metrics.n1 = distinctOperators.count
        metrics.n2 = distinctOperands.count

        return MetricsWithSets(
            metrics: metrics,
            operators: distinctOperators,
            operands: distinctOperands
        )
    }
}

// MARK: - Aggregation

func aggregateTotals(_ results: [MetricsWithSets]) -> HalsteadMetrics {
    var allOperators = Set<String>()
    var allOperands = Set<String>()
    var totalN1 = 0
    var totalN2 = 0

    for result in results {
        allOperators.formUnion(result.operators)
        allOperands.formUnion(result.operands)
        totalN1 += result.metrics.N1
        totalN2 += result.metrics.N2
    }

    var totals = HalsteadMetrics(path: "TOTALS")
    totals.n1 = allOperators.count
    totals.n2 = allOperands.count
    totals.N1 = totalN1
    totals.N2 = totalN2

    return totals
}

// MARK: - Threshold Checking

enum Comparator: String {
    case greaterThan = ">"
    case greaterThanOrEqual = ">="
    case lessThan = "<"
    case lessThanOrEqual = "<="
    case equal = "=="
}

struct Threshold {
    let metric: String
    let comparator: Comparator
    let value: Double
}

func parseThreshold(_ string: String) throws -> Threshold {
    // Try each comparator (order matters - check >= before >)
    let comparators: [(String, Comparator)] = [
        (">=", .greaterThanOrEqual),
        ("<=", .lessThanOrEqual),
        (">", .greaterThan),
        ("<", .lessThan),
        ("==", .equal)
    ]

    for (symbol, comp) in comparators {
        if let range = string.range(of: symbol) {
            let metric = String(string[..<range.lowerBound])
            let valueString = String(string[range.upperBound...])

            guard let value = Double(valueString) else {
                throw CLIError.invalid_threshold(string)
            }

            return Threshold(metric: metric, comparator: comp, value: value)
        }
    }

    throw CLIError.invalid_threshold(string)
}

func checkThresholds(_ metrics: HalsteadMetrics, thresholds: [Threshold]) -> [String] {
    var violations: [String] = []

    for threshold in thresholds {
        guard let actualValue = getMetricValue(metrics, metric: threshold.metric) else {
            violations.append("\(metrics.path): Unknown metric '\(threshold.metric)'")
            continue
        }

        let passes = compareValues(actualValue, threshold.comparator, threshold.value)

        if !passes {
            let violation = "\(metrics.path): \(threshold.metric) = \(String(format: "%.2f", actualValue)), threshold: \(threshold.metric)\(threshold.comparator.rawValue)\(threshold.value)"
            violations.append(violation)
        }
    }

    return violations
}

func getMetricValue(_ metrics: HalsteadMetrics, metric: String) -> Double? {
    guard let key = MetricKey(string: metric) else { return nil }
    return metrics[keyPath: key.keyPath]
}

func compareValues(_ actual: Double, _ comparator: Comparator, _ expected: Double) -> Bool {
    switch comparator {
    case .greaterThan: return actual > expected
    case .greaterThanOrEqual: return actual >= expected
    case .lessThan: return actual < expected
    case .lessThanOrEqual: return actual <= expected
    case .equal: return abs(actual - expected) < 0.01  // Floating point tolerance
    }
}

// MARK: - Architecture Hotspots

struct RiskThresholds {
    static let critical: Double = 5.0
    static let high: Double = 2.0
    static let moderate: Double = 1.0

    enum Category: String {
        case critical, high, moderate, low

        static func categorize(riskScore: Double) -> Category {
            if riskScore >= RiskThresholds.critical { return .critical }
            if riskScore >= RiskThresholds.high { return .high }
            if riskScore >= RiskThresholds.moderate { return .moderate }
            return .low
        }

        var emoji: String {
            switch self {
            case .critical: return "🔴"
            case .high: return "🟡"
            case .moderate: return "🟠"
            case .low: return "🟢"
            }
        }
    }
}

struct DifficultyThresholds {
    static let veryHigh: Double = 60.0
    static let high: Double = 40.0
    static let moderate: Double = 25.0
}

struct DirectoryStats {
    let file_count: Int
    let avg_risk: Double
    let critical_count: Int  // risk >= RiskThresholds.critical
    let high_count: Int      // RiskThresholds.high <= risk < RiskThresholds.critical
    let moderate_count: Int  // RiskThresholds.moderate <= risk < RiskThresholds.high
    let low_count: Int       // risk < RiskThresholds.moderate

    init(files: [HalsteadMetrics]) {
        self.file_count = files.count
        let totalRisk = files.reduce(0.0) { $0 + $1.riskScore }
        self.avg_risk = file_count > 0 ? totalRisk / Double(file_count) : 0.0

        var critical = 0
        var high = 0
        var moderate = 0
        var low = 0

        for file in files {
            if file.riskScore >= RiskThresholds.critical {
                critical += 1
            } else if file.riskScore >= RiskThresholds.high {
                high += 1
            } else if file.riskScore >= RiskThresholds.moderate {
                moderate += 1
            } else {
                low += 1
            }
        }

        self.critical_count = critical
        self.high_count = high
        self.moderate_count = moderate
        self.low_count = low
    }
}

/// Extracts the top-level directory from a file path.
/// Examples:
/// - /Users/foo/Code/project/App/File.swift -> App/
/// - App/Views/File.swift -> App/
/// - main.swift -> .
func extractDirectory(from path: String) -> String {
    if path.hasPrefix("/") {
        // Absolute path - find project directory (last non-file component)
        if let lastSlashIndex = path.lastIndex(of: "/"),
           let secondLastSlashIndex = path[..<lastSlashIndex].lastIndex(of: "/") {
            let startIndex = path.index(after: secondLastSlashIndex)
            return String(path[startIndex...lastSlashIndex])
        } else {
            return "."
        }
    } else {
        // Relative path
        let components = path.split(separator: "/")
        if components.count > 1 {
            return String(components[0]) + "/"
        } else {
            return "."
        }
    }
}

func groupByDirectory(_ fileMetrics: [HalsteadMetrics]) -> [String: [HalsteadMetrics]] {
    var grouped: [String: [HalsteadMetrics]] = [:]

    for metrics in fileMetrics {
        let directory = extractDirectory(from: metrics.path)

        if grouped[directory] == nil {
            grouped[directory] = []
        }
        grouped[directory]?.append(metrics)
    }

    return grouped
}

func formatArchitectureHotspots(_ fileMetrics: [HalsteadMetrics]) -> String {
    var output = ""

    output += """

ARCHITECTURE HOTSPOTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    let grouped = groupByDirectory(fileMetrics)

    var directoryStats: [(directory: String, stats: DirectoryStats)] = []
    for (directory, files) in grouped {
        let stats = DirectoryStats(files: files)
        directoryStats.append((directory: directory, stats: stats))
    }

    directoryStats.sort { lhs, rhs in
        let lhsStats = lhs.stats
        let rhsStats = rhs.stats

        if lhsStats.critical_count != rhsStats.critical_count {
            return lhsStats.critical_count > rhsStats.critical_count
        }
        if lhsStats.high_count != rhsStats.high_count {
            return lhsStats.high_count > rhsStats.high_count
        }
        if lhsStats.moderate_count != rhsStats.moderate_count {
            return lhsStats.moderate_count > rhsStats.moderate_count
        }
        return lhsStats.avg_risk > rhsStats.avg_risk
    }

    for (directory, stats) in directoryStats {
        let emoji: String
        let priorityText: String

        if stats.critical_count > 0 {
            emoji = "🔴"
            priorityText = "\(stats.critical_count) critical"
        } else if stats.high_count > 0 {
            emoji = "🟡"
            priorityText = "\(stats.high_count) high"
        } else if stats.moderate_count > 0 {
            emoji = "🟠"
            priorityText = "\(stats.moderate_count) moderate"
        } else {
            emoji = "🟢"
            priorityText = "Clean (\(stats.file_count) files)"
        }

        let avgRiskStr = String(format: "%.2f", stats.avg_risk)
        let warningIndicator = stats.avg_risk >= RiskThresholds.high ? "  ⚠️  Priority" : (stats.avg_risk >= RiskThresholds.moderate ? "  ⚠️" : "")

        // Build output line with manual padding
        func pad(_ s: String, to width: Int) -> String {
            let paddingNeeded = width - s.count
            return paddingNeeded > 0 ? s + String(repeating: " ", count: paddingNeeded) : s
        }

        let directoryCol = pad(directory, to: 13)
        let priorityCol = pad(priorityText, to: 20)
        let avgCol = pad(avgRiskStr, to: 6)

        output += "📁 \(directoryCol) \(emoji) \(priorityCol) │ Avg: \(avgCol)\(warningIndicator)\n"
    }

    return output
}

// MARK: - Output Formatting

struct OutputSchema: Codable {
    let files: [HalsteadMetrics]
    let totals: HalsteadMetrics
}

func formatAsJSON(_ fileMetrics: [HalsteadMetrics], totals: HalsteadMetrics) -> String {
    let output = OutputSchema(files: fileMetrics, totals: totals)
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]

    guard let data = try? encoder.encode(output),
          let json = String(data: data, encoding: .utf8) else {
        return "{}"
    }

    return json
}

func formatAsTable(_ fileMetrics: [HalsteadMetrics], totals: HalsteadMetrics) -> String {
    func pad(_ string: String, to width: Int, rightAlign: Bool = false) -> String {
        if string.count >= width { return string }
        let padding = String(repeating: " ", count: width - string.count)
        return rightAlign ? padding + string : string + padding
    }

    func formatRow(path: String, vocab: Int, length: Int, volume: Double,
                   difficulty: Double, effort: Double, time: Double, riskScore: Double) -> String {
        return pad(path, to: 50) + " " +
               pad(String(vocab), to: 8, rightAlign: true) + " " +
               pad(String(length), to: 8, rightAlign: true) + " " +
               pad(String(format: "%.2f", volume), to: 12, rightAlign: true) + " " +
               pad(String(format: "%.2f", difficulty), to: 12, rightAlign: true) + " " +
               pad(String(format: "%.2f", effort), to: 12, rightAlign: true) + " " +
               pad(String(format: "%.2f", time), to: 10, rightAlign: true) + " " +
               pad(String(format: "%.2f", riskScore), to: 8, rightAlign: true)
    }

    var output = ""

    // Header - manually build it to avoid string replacement issues
    let header = pad("Path", to: 50) + " " +
                pad("n", to: 8, rightAlign: true) + " " +
                pad("N", to: 8, rightAlign: true) + " " +
                pad("Volume", to: 12, rightAlign: true) + " " +
                pad("Difficulty", to: 12, rightAlign: true) + " " +
                pad("Effort", to: 12, rightAlign: true) + " " +
                pad("Time(s)", to: 10, rightAlign: true) + " " +
                pad("Risk", to: 8, rightAlign: true)

    output += header + "\n"
    output += String(repeating: "-", count: 135) + "\n"

    // Files
    for metrics in fileMetrics {
        output += formatRow(path: metrics.path, vocab: metrics.vocabulary, length: metrics.length,
                          volume: metrics.volume, difficulty: metrics.difficulty,
                          effort: metrics.effort, time: metrics.timeSeconds, riskScore: metrics.riskScore) + "\n"
    }

    return output
}

func formatRiskDistribution(_ fileMetrics: [HalsteadMetrics]) -> String {
    var output = ""

    // Categorize files
    let critical = fileMetrics.filter { $0.riskScore >= RiskThresholds.critical }
    let high = fileMetrics.filter { $0.riskScore >= RiskThresholds.high && $0.riskScore < RiskThresholds.critical }
    let moderate = fileMetrics.filter { $0.riskScore >= RiskThresholds.moderate && $0.riskScore < RiskThresholds.high }
    let low = fileMetrics.filter { $0.riskScore < RiskThresholds.moderate }

    let total = fileMetrics.count
    let focusCount = critical.count + high.count

    // Calculate percentages
    let criticalPct = total > 0 ? (critical.count * 100) / total : 0
    let highPct = total > 0 ? (high.count * 100) / total : 0
    let moderatePct = total > 0 ? (moderate.count * 100) / total : 0
    let lowPct = total > 0 ? (low.count * 100) / total : 0

    // Fixed bar width (50 chars) - bars proportional to PERCENTAGE
    func makeBar(_ percentage: Int) -> String {
        guard percentage > 0 else { return "" }
        let blocks = Int(round(Double(percentage) * 50.0 / 100.0))
        return String(repeating: "▓", count: max(1, blocks))
    }

    // Helper for file count label
    func fileLabel(_ count: Int) -> String {
        return count == 1 ? "1 file " : "\(count) files"
    }

    output += "RISK DISTRIBUTION\n"
    output += String(repeating: "━", count: 62) + "\n"
    output += "🔴 Critical (≥5.0)     \(fileLabel(critical.count))  \(makeBar(criticalPct))  \(criticalPct)%  │\n"
    output += "🟡 High (2.0-5.0)      \(fileLabel(high.count))  \(makeBar(highPct))  \(highPct)%  │ ⚠️  Focus: \(focusCount) files\n"
    output += "🟠 Moderate (1.0-2.0)  \(fileLabel(moderate.count))  \(makeBar(moderatePct))  \(moderatePct)% │\n"
    output += "🟢 Low (<1.0)          \(fileLabel(low.count))  \(makeBar(lowPct))  \(lowPct)% │\n"

    return output
}

func formatSummaryHeader(fileCount: Int, projectAvg: Double, needsAttentionText: String) -> String {
    return """
╔═══════════════════════════════════════════════════════════╗
║ SwiftHAL - Halstead Complexity Analyzer                   ║
║ Measures code complexity via operator/operand analysis    ║
║ Risk score correlates with defect probability             ║
╚═══════════════════════════════════════════════════════════╝

\(fileCount) files analyzed │ Project avg: \(String(format: "%.2f", projectAvg)) │ \(needsAttentionText)

"""
}

func formatFilesNeedingAttention(_ criticalAndHighFiles: [HalsteadMetrics], projectAvg: Double) -> String {
    guard !criticalAndHighFiles.isEmpty else { return "" }

    var output = "⚠️  Files Needing Attention\n\n"
    for metrics in criticalAndHighFiles {
        output += "  \(shortPath(metrics.path))\n"

        let comparison = projectAvg > 0 ? metrics.riskScore / projectAvg : 0
        let volumeFormatted = formatWithThousandsSeparator(Int(metrics.volume))

        output += "  Risk: \(String(format: "%.1f", metrics.riskScore))  │  Vol: \(volumeFormatted)  │  Diff: \(String(format: "%.1f", metrics.difficulty))  │  ↑ \(String(format: "%.1f", comparison))× project avg\n\n"
    }
    return output
}

func formatWellFactoredFiles(_ fileMetrics: [HalsteadMetrics]) -> String {
    let topBest = fileMetrics.sorted(by: { $0.riskScore < $1.riskScore }).prefix(3)
    guard !topBest.isEmpty else { return "" }

    var output = "✓  Well-Factored Files\n\n"
    for metrics in topBest {
        output += "  • \(shortPath(metrics.path)) (\(String(format: "%.2f", metrics.riskScore)) risk)\n"
    }
    output += "\n"
    return output
}

func formatProjectSummary(avgRisk: Double, medianRisk: Double, maxRisk: Double, vocabulary: Int, needsAttentionCount: Int, needsAttentionPct: Int, focusAreas: [String]) -> String {
    var output = "────────────────────────────────────────────────────────────\n"
    output += "📊 PROJECT SUMMARY\n\n"
    output += "  Complexity    \(String(format: "%.2f", avgRisk)) avg  │  \(String(format: "%.2f", medianRisk)) median  │  \(String(format: "%.2f", maxRisk)) max\n"
    output += "  Vocabulary    \(String(vocabulary).replacingOccurrences(of: "(\\d)(?=(\\d{3})+$)", with: "$1,", options: .regularExpression)) distinct symbols\n"
    output += "  Health        \(needsAttentionCount) files need attention (\(needsAttentionPct)% of codebase)\n"
    if !focusAreas.isEmpty {
        output += "  Focus Areas   \(focusAreas.joined(separator: ", "))\n"
    }
    return output
}

func formatAsSummary(_ fileMetrics: [HalsteadMetrics], totals: HalsteadMetrics, verbose: Bool) -> String {
    var output = ""

    // Health status
    let healthStatus = getHealthStatus(totals: totals, fileCount: fileMetrics.count)
    // Files needing attention: risk >= moderate (for count), but display only >= high
    let filesNeedingAttention = fileMetrics.filter { $0.riskScore >= RiskThresholds.moderate }
    let criticalAndHighFiles = fileMetrics.filter { $0.riskScore >= RiskThresholds.high }
    let needsAttentionCount = filesNeedingAttention.count
    let needsAttentionText = needsAttentionCount == 1 ? "1 file needs attention" : "\(needsAttentionCount) files need attention"
    let projectAvg = totals.riskScore / Double(fileMetrics.count)

    // Header
    output += formatSummaryHeader(fileCount: fileMetrics.count, projectAvg: projectAvg, needsAttentionText: needsAttentionText)

    // Risk distribution and architecture hotspots
    output += "\n" + formatRiskDistribution(fileMetrics) + "\n"
    output += formatArchitectureHotspots(fileMetrics) + "\n"

    if verbose {
        // Show all files
        output += "All Files\n\n"
        for metrics in fileMetrics.sorted(by: { $0.riskScore > $1.riskScore }) {
            output += formatFileLine(metrics)
        }
    } else {
        // Files needing attention and well-factored files
        let criticalAndHigh = criticalAndHighFiles.sorted(by: { $0.riskScore > $1.riskScore })
        output += formatFilesNeedingAttention(criticalAndHigh, projectAvg: projectAvg)
        output += formatWellFactoredFiles(fileMetrics)
    }

    // Project Summary
    let avgRisk = totals.riskScore / Double(fileMetrics.count)
    let medianRisk = calculateMedianRisk(fileMetrics)
    let maxRisk = calculateMaxRisk(fileMetrics)
    let focusAreas = extractFocusAreas(fileMetrics)
    let needsAttentionPct = filesNeedingAttention.count * 100 / fileMetrics.count

    output += formatProjectSummary(
        avgRisk: avgRisk,
        medianRisk: medianRisk,
        maxRisk: maxRisk,
        vocabulary: totals.vocabulary,
        needsAttentionCount: needsAttentionCount,
        needsAttentionPct: needsAttentionPct,
        focusAreas: focusAreas
    )

    return output
}

func getHealthStatus(totals: HalsteadMetrics, fileCount: Int) -> String {
    let avgRisk = totals.riskScore / Double(fileCount)
    if avgRisk < RiskThresholds.moderate { return "Good" }
    if avgRisk < RiskThresholds.high { return "Fair" }
    if avgRisk < RiskThresholds.critical { return "Needs Review" }
    return "Critical"
}

func calculateMedianRisk(_ fileMetrics: [HalsteadMetrics]) -> Double {
    guard !fileMetrics.isEmpty else { return 0.0 }
    let sorted_risks = fileMetrics.map { $0.riskScore }.sorted()
    let count = sorted_risks.count
    if count % 2 == 0 {
        return (sorted_risks[count / 2 - 1] + sorted_risks[count / 2]) / 2.0
    } else {
        return sorted_risks[count / 2]
    }
}

func calculateMaxRisk(_ fileMetrics: [HalsteadMetrics]) -> Double {
    return fileMetrics.map { $0.riskScore }.max() ?? 0.0
}

func extractFocusAreas(_ fileMetrics: [HalsteadMetrics]) -> [String] {
    let high_risk_files = fileMetrics.filter { $0.riskScore >= RiskThresholds.high }
    var directories = Set<String>()

    for metrics in high_risk_files {
        let directory = extractDirectory(from: metrics.path)

        if directory != "." {
            directories.insert(directory)
        }
    }

    return Array(directories).sorted()
}

func difficultyLabel(_ difficulty: Double) -> String {
    if difficulty > DifficultyThresholds.veryHigh { return "Very High" }
    if difficulty > DifficultyThresholds.high { return "High" }
    if difficulty > DifficultyThresholds.moderate { return "Moderate" }
    return "Low"
}

func shortPath(_ path: String) -> String {
    let components = path.split(separator: "/")
    if components.count > 2 {
        return components.suffix(2).joined(separator: "/")
    }
    return path
}

func formatWithThousandsSeparator(_ value: Int) -> String {
    let formatter = NumberFormatter()
    formatter.numberStyle = .decimal
    formatter.groupingSeparator = ","
    return formatter.string(from: NSNumber(value: value)) ?? String(value)
}

func formatFileLine(_ metrics: HalsteadMetrics) -> String {
    return "  \(shortPath(metrics.path))\n" +
           "     Risk: \(String(format: "%.2f", metrics.riskScore)) • " +
           "Difficulty: \(String(format: "%.1f", metrics.difficulty))\n\n"
}

func recommendation(for metrics: HalsteadMetrics) -> String? {
    if metrics.riskScore >= RiskThresholds.critical {
        return "Critical - immediate refactoring needed"
    }
    if metrics.riskScore >= RiskThresholds.high {
        return "High - review recommended"
    }
    if metrics.riskScore >= RiskThresholds.moderate {
        return "Moderate - monitor complexity"
    }
    return nil
}

// MARK: - CLI Options

enum OutputFormat: String, ExpressibleByArgument {
    case json
    case table
    case summary
}

struct CLIOptions {
    var path: String = "."
    var format: OutputFormat = .summary
    var thresholds: [String]? = nil
    var output_path: String? = nil
    var include_tests: Bool = false
    var show_help: Bool = false
    var show_explanation: Bool = false
    var verbose: Bool = false
    var include: String? = nil
    var exclude: String? = nil
}

enum CLIError: Error {
    case invalid_format(String)
    case missing_value(String)
    case invalid_threshold(String)
}

// parseArguments removed - replaced by ArgumentParser in @main SwiftHAL struct
// For tests, use: SwiftHAL.parseAsRoot(["arg1", "arg2"]) or create CLIOptions directly
func parseArguments(_ args: [String]) throws -> CLIOptions {
    // Stub for test compatibility
    // Note: --help and --explain will cause ArgumentParser to exit, so handle those specially
    let argsArray = Array(args.dropFirst())

    // Check for help or explain flags
    if argsArray.contains("--help") || argsArray.contains("-h") {
        return CLIOptions(path: ".", format: .summary, thresholds: nil, output_path: nil,
                         include_tests: false, show_help: true, show_explanation: false,
                         verbose: false, include: nil, exclude: nil)
    }
    if argsArray.contains("--explain") {
        return CLIOptions(path: ".", format: .summary, thresholds: nil, output_path: nil,
                         include_tests: false, show_help: false, show_explanation: true,
                         verbose: false, include: nil, exclude: nil)
    }

    // Parse normally for other args
    guard let command = try SwiftHAL.parseAsRoot(argsArray) as? SwiftHAL else {
        fatalError("parseAsRoot should return SwiftHAL instance")
    }
    // Use the computed path property that handles pathOption ?? pathArgument ?? "."
    let resolvedPath = command.pathOption ?? command.pathArgument ?? "."
    return CLIOptions(
        path: resolvedPath,
        format: command.format,
        thresholds: command.threshold?.split(separator: ",").map(String.init),
        output_path: command.output,
        include_tests: command.includeTests,
        show_help: false,  // ArgumentParser handles help automatically
        show_explanation: command.explain,
        verbose: command.verbose,
        include: command.include,
        exclude: command.exclude
    )
}

// printUsage removed - ArgumentParser provides automatic --help generation

func printMetricsExplanation() {
    print("""

    SwiftHAL Metrics Explained
    ══════════════════════════════════════════════════════════════

    BASIC COUNTS
    ────────────────────────────────────────────────────────────
    n1              Distinct operators (keywords, symbols)
    n2              Distinct operands (identifiers, literals)
    N1              Total operators
    N2              Total operands

    DERIVED METRICS
    ────────────────────────────────────────────────────────────
    Vocabulary      n1 + n2 (unique symbols in your code)
    Length          N1 + N2 (total symbols)
    Volume          Length × log₂(Vocabulary)
                    Measures code size accounting for complexity

    Difficulty      (n1/2) × (N2/n2)
                    How hard to write or understand
                    Higher = more complex logic

    Effort          Difficulty × Volume
                    Mental effort required to develop/maintain

    Time            Effort / 18 (seconds)
                    Estimated programming time

    Risk Score      Volume / 3000
                    Statistical defect density estimate
                    ⚠️  NOT actual bugs - probability measure

    INTERPRETING RISK SCORE
    ────────────────────────────────────────────────────────────
    < 0.5           Very low complexity - simple utility code
    0.5 - 1.0       Low complexity - straightforward logic
    1.0 - 2.0       Moderate - typical business logic
    2.0 - 5.0       High - review recommended
    > 5.0           Very high - strong refactoring candidate

    PRACTICAL USE
    ────────────────────────────────────────────────────────────
    • Prioritize code reviews on high risk score files
    • Allocate more testing to complex modules
    • Track trends over time (is complexity growing?)
    • Identify refactoring opportunities

    Learn more: https://en.wikipedia.org/wiki/Halstead_complexity_measures
    """)
}

@main
struct SwiftHAL: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "hal",
        abstract: "Halstead Metrics Calculator for Swift",
        discussion: """
            Analyzes Swift code to calculate Halstead complexity metrics.
            Risk score correlates with defect probability.
            """
    )

    @Option(name: .customLong("path"), help: "Path to analyze (directory or file)")
    var pathOption: String?

    @Argument(help: "Path to analyze (directory or file) [deprecated: use --path]")
    var pathArgument: String?

    private var path: String {
        return pathOption ?? pathArgument ?? "."
    }

    @Option(name: .long, help: "Output format: json, table, summary")
    var format: OutputFormat = .summary

    @Option(name: .long, help: "Threshold conditions (e.g., 'volume>800,difficulty>20')")
    var threshold: String?

    @Option(name: .long, help: "Write output to file instead of stdout")
    var output: String?

    @Option(name: .long, help: "Include glob pattern (e.g., '**/*.swift')")
    var include: String?

    @Option(name: .long, help: "Exclude glob pattern (e.g., 'Tests/**')")
    var exclude: String?

    @Flag(name: .long, help: "Include test files (default: excluded)")
    var includeTests = false

    @Flag(name: [.short, .long], help: "Show all files in summary output")
    var verbose = false

    @Flag(name: .long, help: "Show detailed explanation of metrics")
    var explain = false

    mutating func run() throws {
        if explain {
            printMetricsExplanation()
            return
        }

        // Convert to CLIOptions for compatibility with helper functions
        let options = CLIOptions(
            path: path,
            format: format,
            thresholds: threshold?.split(separator: ",").map(String.init),
            output_path: output,
            include_tests: includeTests,
            show_help: false,
            show_explanation: false,
            verbose: verbose,
            include: include,
            exclude: exclude
        )

        try SwiftHAL.runAnalysis(options: options)
    }

    static func runAnalysis(options: CLIOptions) throws {
        let fileManager = FileManager.default
        let rootURL = URL(fileURLWithPath: options.path)

        // Validate path exists
        var isDirectory: ObjCBool = false
        guard fileManager.fileExists(atPath: rootURL.path, isDirectory: &isDirectory) else {
            print("Error: Path does not exist: \(rootURL.path)")
            Darwin.exit(1)
        }

        // Show what directory we're analyzing
        let absolutePath = rootURL.standardizedFileURL.path
        if options.format != .summary {
            print("Analyzing Swift files in: \(absolutePath)")
        }

        let swiftFiles = findSwiftFiles(at: rootURL, options: options, fileManager: fileManager)
        let calculator = MetricsCalculator()

        if options.format != .summary {
            print("Found \(swiftFiles.count) Swift files...")
        }

        var allResults: [MetricsWithSets] = []

        for fileURL in swiftFiles {
            do {
                let result = try calculator.calculateWithSets(for: fileURL)
                allResults.append(result)

                if options.format != .summary {
                    let metrics = result.metrics
                    print("File: \(metrics.path)")
                    print("  Vocabulary: \(metrics.vocabulary), Length: \(metrics.length), Volume: \(String(format: "%.2f", metrics.volume))")
                    print("  Difficulty: \(String(format: "%.2f", metrics.difficulty)), Effort: \(String(format: "%.2f", metrics.effort)), Risk Score: \(String(format: "%.2f", metrics.riskScore))")
                }
            } catch {
                print("Error calculating metrics for \(fileURL.path): \(error)")
            }
        }

        // Compute and display output
        if !allResults.isEmpty {
            let totals = aggregateTotals(allResults)
            let fileMetrics = allResults.map { $0.metrics }

            // Generate output based on format
            let output: String
            if options.format == .summary {
                output = formatAsSummary(fileMetrics, totals: totals, verbose: options.verbose)
            } else if options.format == .json {
                output = formatAsJSON(fileMetrics, totals: totals)
            } else {
                output = formatAsTable(fileMetrics, totals: totals)
            }

            if let output_path = options.output_path {
                try output.write(toFile: output_path, atomically: true, encoding: .utf8)
                print("Output written to \(output_path)")
            } else {
                print(output)
            }

            // Check thresholds
            if let threshold_strings = options.thresholds {
                let thresholds = try threshold_strings.map { try parseThreshold($0) }
                var all_violations: [String] = []

                // Check individual files
                    for result in allResults {
                        let violations = checkThresholds(result.metrics, thresholds: thresholds)
                        all_violations.append(contentsOf: violations)
                    }

                    // Check totals
                    let totals_violations = checkThresholds(totals, thresholds: thresholds)
                    all_violations.append(contentsOf: totals_violations)

                    if !all_violations.isEmpty {
                        print("\nThreshold violations:")
                        for violation in all_violations {
                            print("  \(violation)")
                        }
                        Darwin.exit(2)
                    }
                }
            }
    }

    /// Recursively finds all Swift files in a given directory.
    static func findSwiftFiles(at rootURL: URL, options: CLIOptions, fileManager: FileManager) -> [URL] {
        var swiftFiles: [URL] = []
        let enumerator = fileManager.enumerator(at: rootURL,
                                               includingPropertiesForKeys: [.isRegularFileKey],
                                               options: [.skipsHiddenFiles, .skipsPackageDescendants])

        guard let fileEnumerator = enumerator else {
            print("Error: Could not enumerate files at \(rootURL.path)")
            return []
        }

        for case let fileURL as URL in fileEnumerator {
            do {
                let resourceValues = try fileURL.resourceValues(forKeys: [.isRegularFileKey])
                if resourceValues.isRegularFile == true && fileURL.pathExtension == "swift" {
                    // Apply exclusion filters
                    if shouldExcludeFile(fileURL, options: options) {
                        continue
                    }
                    swiftFiles.append(fileURL)
                }
            } catch {
                print("Error processing file attributes for \(fileURL.path): \(error)")
            }
        }
        return swiftFiles
    }

    /// Determines if a file should be excluded based on CLI options.
    static func shouldExcludeFile(_ fileURL: URL, options: CLIOptions) -> Bool {
        let path = fileURL.path

        // Always exclude Package.swift (not analyzable code)
        if fileURL.lastPathComponent == "Package.swift" {
            return true
        }

        // If include_tests is true, don't apply test exclusions
        if options.include_tests {
            return false
        }

        // Default exclusions (when include_tests is false):

        // Exclude files ending in Tests.swift
        if fileURL.lastPathComponent.hasSuffix("Tests.swift") {
            return true
        }

        // Exclude files in any /Tests/ directory
        let pathComponents = fileURL.pathComponents
        if pathComponents.contains("Tests") {
            return true
        }

        return false
    }
}

