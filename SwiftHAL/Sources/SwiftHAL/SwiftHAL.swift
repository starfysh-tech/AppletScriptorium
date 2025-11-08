import Foundation
import SwiftSyntax
import SwiftParser

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
        let actualValue = getMetricValue(metrics, metric: threshold.metric)
        let passes = compareValues(actualValue, threshold.comparator, threshold.value)

        if !passes {
            let violation = "\(metrics.path): \(threshold.metric) = \(String(format: "%.2f", actualValue)), threshold: \(threshold.metric)\(threshold.comparator.rawValue)\(threshold.value)"
            violations.append(violation)
        }
    }

    return violations
}

func getMetricValue(_ metrics: HalsteadMetrics, metric: String) -> Double {
    switch metric.lowercased() {
    case "n1": return Double(metrics.n1)
    case "n2": return Double(metrics.n2)
    case "n", "vocabulary": return Double(metrics.vocabulary)
    case "length": return Double(metrics.length)
    case "volume": return metrics.volume
    case "difficulty": return metrics.difficulty
    case "effort": return metrics.effort
    case "time", "timeseconds": return metrics.timeSeconds
    case "riskscore": return metrics.riskScore
    case "estimatedlength": return metrics.estimatedLength
    default: return 0.0
    }
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

struct DirectoryStats {
    let file_count: Int
    let avg_risk: Double
    let critical_count: Int  // risk >= 5.0
    let high_count: Int      // 2.0 <= risk < 5.0
    let moderate_count: Int  // 1.0 <= risk < 2.0
    let low_count: Int       // risk < 1.0

    init(files: [HalsteadMetrics]) {
        self.file_count = files.count
        let totalRisk = files.reduce(0.0) { $0 + $1.riskScore }
        self.avg_risk = file_count > 0 ? totalRisk / Double(file_count) : 0.0

        var critical = 0
        var high = 0
        var moderate = 0
        var low = 0

        for file in files {
            if file.riskScore >= 5.0 {
                critical += 1
            } else if file.riskScore >= 2.0 {
                high += 1
            } else if file.riskScore >= 1.0 {
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

func group_by_directory(_ fileMetrics: [HalsteadMetrics]) -> [String: [HalsteadMetrics]] {
    var grouped: [String: [HalsteadMetrics]] = [:]

    for metrics in fileMetrics {
        let components = metrics.path.split(separator: "/")
        let directory: String

        // For absolute paths (starting with /), find the last directory component
        // /Users/foo/Code/project/App/File.swift -> App/
        // For relative paths:
        // App/Views/File.swift -> App/
        // main.swift -> .
        if metrics.path.hasPrefix("/") {
            // Absolute path - find project directory (last non-file component)
            if let lastSlashIndex = metrics.path.lastIndex(of: "/"),
               let secondLastSlashIndex = metrics.path[..<lastSlashIndex].lastIndex(of: "/") {
                let startIndex = metrics.path.index(after: secondLastSlashIndex)
                directory = String(metrics.path[startIndex...lastSlashIndex])
            } else {
                directory = "."
            }
        } else {
            // Relative path
            if components.count > 1 {
                directory = String(components[0]) + "/"
            } else {
                directory = "."
            }
        }

        if grouped[directory] == nil {
            grouped[directory] = []
        }
        grouped[directory]?.append(metrics)
    }

    return grouped
}

func format_architecture_hotspots(_ fileMetrics: [HalsteadMetrics]) -> String {
    var output = ""

    output += """

ARCHITECTURE HOTSPOTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    let grouped = group_by_directory(fileMetrics)

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
        let warningIndicator = stats.avg_risk >= 2.0 ? "  ⚠️  Priority" : (stats.avg_risk >= 1.0 ? "  ⚠️" : "")

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

func format_risk_distribution(_ fileMetrics: [HalsteadMetrics]) -> String {
    var output = ""

    // Categorize files
    let critical = fileMetrics.filter { $0.riskScore >= 5.0 }
    let high = fileMetrics.filter { $0.riskScore >= 2.0 && $0.riskScore < 5.0 }
    let moderate = fileMetrics.filter { $0.riskScore >= 1.0 && $0.riskScore < 2.0 }
    let low = fileMetrics.filter { $0.riskScore < 1.0 }

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

func formatAsSummary(_ fileMetrics: [HalsteadMetrics], totals: HalsteadMetrics, verbose: Bool) -> String {
    var output = ""

    // Health status
    let healthStatus = getHealthStatus(totals: totals, fileCount: fileMetrics.count)
    // Files needing attention: risk >= 1.0 (for count), but display only >= 2.0
    let filesNeedingAttention = fileMetrics.filter { $0.riskScore >= 1.0 }
    let criticalAndHighFiles = fileMetrics.filter { $0.riskScore >= 2.0 }
    let needsAttentionCount = filesNeedingAttention.count
    let needsAttentionText = needsAttentionCount == 1 ? "1 file needs attention" : "\(needsAttentionCount) files need attention"

    output += """
╔═══════════════════════════════════════════════════════════╗
║ SwiftHAL - Halstead Complexity Analyzer                   ║
║ Measures code complexity via operator/operand analysis    ║
║ Risk score correlates with defect probability             ║
╚═══════════════════════════════════════════════════════════╝

\(fileMetrics.count) files analyzed │ Project avg: \(String(format: "%.2f", totals.riskScore / Double(fileMetrics.count))) │ \(needsAttentionText)

"""

    // Risk distribution
    output += "\n" + format_risk_distribution(fileMetrics) + "\n"
    // Architecture hotspots
    output += format_architecture_hotspots(fileMetrics) + "\n"

    if verbose {
        // Show all files
        output += "All Files\n\n"
        for metrics in fileMetrics.sorted(by: { $0.riskScore > $1.riskScore }) {
            output += formatFileLine(metrics)
        }
    } else {
        // Calculate project average for comparison
        let projectAvg = totals.riskScore / Double(fileMetrics.count)

        // ALL critical and high files (risk >= 2.0), no limit
        let criticalAndHigh = criticalAndHighFiles.sorted(by: { $0.riskScore > $1.riskScore })
        if !criticalAndHigh.isEmpty {
            output += "⚠️  Files Needing Attention\n\n"
            for metrics in criticalAndHigh {
                output += "  \(shortPath(metrics.path))\n"

                let comparison = projectAvg > 0 ? metrics.riskScore / projectAvg : 0
                let volumeFormatted = format_with_thousands_separator(Int(metrics.volume))

                output += "  Risk: \(String(format: "%.1f", metrics.riskScore))  │  Vol: \(volumeFormatted)  │  Diff: \(String(format: "%.1f", metrics.difficulty))  │  ↑ \(String(format: "%.1f", comparison))× project avg\n\n"
            }
        }

        // Bottom 3 best files
        let topBest = fileMetrics.sorted(by: { $0.riskScore < $1.riskScore }).prefix(3)
        if !topBest.isEmpty {
            output += "✓  Well-Factored Files\n\n"
            for metrics in topBest {
                output += "  • \(shortPath(metrics.path)) (\(String(format: "%.2f", metrics.riskScore)) risk)\n"
            }
            output += "\n"
        }
    }

    // Project Summary
    let avg_risk = totals.riskScore / Double(fileMetrics.count)
    let median_risk = calculate_median_risk(fileMetrics)
    let max_risk = calculate_max_risk(fileMetrics)
    let focus_areas = extract_focus_areas(fileMetrics)
    let needs_attention_pct = filesNeedingAttention.count * 100 / fileMetrics.count

    output += "────────────────────────────────────────────────────────────\n"
    output += "📊 PROJECT SUMMARY\n\n"
    output += "  Complexity    \(String(format: "%.2f", avg_risk)) avg  │  \(String(format: "%.2f", median_risk)) median  │  \(String(format: "%.2f", max_risk)) max\n"
    output += "  Vocabulary    \(String(totals.vocabulary).replacingOccurrences(of: "(\\d)(?=(\\d{3})+$)", with: "$1,", options: .regularExpression)) distinct symbols\n"
    output += "  Health        \(needsAttentionCount) files need attention (\(needs_attention_pct)% of codebase)\n"
    if !focus_areas.isEmpty {
        output += "  Focus Areas   \(focus_areas.joined(separator: ", "))\n"
    }

    return output
}

func getHealthStatus(totals: HalsteadMetrics, fileCount: Int) -> String {
    let avgRisk = totals.riskScore / Double(fileCount)
    if avgRisk < 1.0 { return "Good" }
    if avgRisk < 2.0 { return "Fair" }
    if avgRisk < 5.0 { return "Needs Review" }
    return "Critical"
}

func calculate_median_risk(_ fileMetrics: [HalsteadMetrics]) -> Double {
    guard !fileMetrics.isEmpty else { return 0.0 }
    let sorted_risks = fileMetrics.map { $0.riskScore }.sorted()
    let count = sorted_risks.count
    if count % 2 == 0 {
        return (sorted_risks[count / 2 - 1] + sorted_risks[count / 2]) / 2.0
    } else {
        return sorted_risks[count / 2]
    }
}

func calculate_max_risk(_ fileMetrics: [HalsteadMetrics]) -> Double {
    return fileMetrics.map { $0.riskScore }.max() ?? 0.0
}

func extract_focus_areas(_ fileMetrics: [HalsteadMetrics]) -> [String] {
    let high_risk_files = fileMetrics.filter { $0.riskScore >= 2.0 }
    var directories = Set<String>()

    for metrics in high_risk_files {
        // Use same logic as group_by_directory to extract directory name
        let directory: String

        if metrics.path.hasPrefix("/") {
            // Absolute path - find project directory (last non-file component)
            if let lastSlashIndex = metrics.path.lastIndex(of: "/"),
               let secondLastSlashIndex = metrics.path[..<lastSlashIndex].lastIndex(of: "/") {
                let startIndex = metrics.path.index(after: secondLastSlashIndex)
                directory = String(metrics.path[startIndex...lastSlashIndex])
            } else {
                directory = "."
            }
        } else {
            // Relative path
            let components = metrics.path.split(separator: "/")
            if components.count > 1 {
                directory = String(components[0]) + "/"
            } else {
                directory = "."
            }
        }

        if directory != "." {
            directories.insert(directory)
        }
    }

    return Array(directories).sorted()
}

func difficultyLabel(_ difficulty: Double) -> String {
    if difficulty > 60 { return "Very High" }
    if difficulty > 40 { return "High" }
    if difficulty > 25 { return "Moderate" }
    return "Low"
}

func shortPath(_ path: String) -> String {
    let components = path.split(separator: "/")
    if components.count > 2 {
        return components.suffix(2).joined(separator: "/")
    }
    return path
}

func format_with_thousands_separator(_ value: Int) -> String {
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
    if metrics.riskScore >= 5.0 {
        return "Critical - immediate refactoring needed"
    }
    if metrics.riskScore >= 2.0 {
        return "High - review recommended"
    }
    if metrics.riskScore >= 1.0 {
        return "Moderate - monitor complexity"
    }
    return nil
}

// MARK: - CLI Options

enum OutputFormat: String {
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

func parse_arguments(_ args: [String]) throws -> CLIOptions {
    var options = CLIOptions()
    var i = 1 // Skip program name

    while i < args.count {
        let arg = args[i]

        switch arg {
        case "--path":
            guard i + 1 < args.count else {
                throw CLIError.missing_value("--path")
            }
            options.path = args[i + 1]
            i += 2

        case "--format":
            guard i + 1 < args.count else {
                throw CLIError.missing_value("--format")
            }
            guard let format = OutputFormat(rawValue: args[i + 1]) else {
                throw CLIError.invalid_format(args[i + 1])
            }
            options.format = format
            i += 2

        case "--threshold":
            guard i + 1 < args.count else {
                throw CLIError.missing_value("--threshold")
            }
            let threshold_string = args[i + 1]
            options.thresholds = threshold_string.split(separator: ",").map(String.init)
            i += 2

        case "--output":
            guard i + 1 < args.count else {
                throw CLIError.missing_value("--output")
            }
            options.output_path = args[i + 1]
            i += 2

        case "--include":
            guard i + 1 < args.count else {
                throw CLIError.missing_value("--include")
            }
            options.include = args[i + 1]
            i += 2

        case "--exclude":
            guard i + 1 < args.count else {
                throw CLIError.missing_value("--exclude")
            }
            options.exclude = args[i + 1]
            i += 2

        case "--include-tests":
            options.include_tests = true
            i += 1

        case "--help", "-h":
            options.show_help = true
            i += 1

        case "--explain":
            options.show_explanation = true
            i += 1

        case "--verbose", "-v":
            options.verbose = true
            i += 1

        default:
            // Treat as positional path argument if it doesn't start with --
            if !arg.hasPrefix("-") {
                options.path = arg
            }
            // Otherwise ignore unknown flags
            i += 1
        }
    }

    return options
}

func print_usage() {
    print("""
    SwiftHAL - Halstead Metrics Calculator for Swift

    USAGE:
        hal [options]

    OPTIONS:
        --path <dir-or-file>      Path to analyze (default: .)
        --format <json|table>     Output format (default: table)
        --threshold <conditions>  Threshold conditions (e.g., 'volume>800,difficulty>20')
        --output <path>           Write output to file instead of stdout
        --include <pattern>       Include glob pattern (e.g., '**/*.swift')
        --exclude <pattern>       Exclude glob pattern (e.g., 'Tests/**')
        --include-tests           Include test files (default: excluded)
        --explain                 Show detailed explanation of metrics
        --help, -h                Show this help message

    DEFAULT EXCLUSIONS:
        - **/Tests/** directories
        - **/*Tests.swift files
        - Package.swift (not analyzable code)

    EXAMPLES:
        hal --path ./Sources --format json > halstead.json
        hal --path . --format table
        hal --path . --threshold 'volume>800,difficulty>25'
        hal --include-tests  # Include test files in analysis
        hal --explain
    """)
}

func print_metrics_explanation() {
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
struct SwiftHAL {

    static func main() {
        do {
            let options = try parse_arguments(CommandLine.arguments)

            if options.show_help {
                print_usage()
                exit(0)
            }

            if options.show_explanation {
                print_metrics_explanation()
                exit(0)
            }

            let fileManager = FileManager.default
            let rootURL = URL(fileURLWithPath: options.path)

            // Validate path exists
            var isDirectory: ObjCBool = false
            guard fileManager.fileExists(atPath: rootURL.path, isDirectory: &isDirectory) else {
                print("Error: Path does not exist: \(rootURL.path)")
                exit(1)
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
                        exit(2)
                    }
                }
            }
        } catch {
            print("Error: \(error)")
            exit(1)
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
                    if should_exclude_file(fileURL, options: options) {
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
    static func should_exclude_file(_ fileURL: URL, options: CLIOptions) -> Bool {
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

