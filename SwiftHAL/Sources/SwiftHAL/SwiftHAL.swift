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

    // Totals
    output += String(repeating: "-", count: 135) + "\n"
    output += formatRow(path: totals.path, vocab: totals.vocabulary, length: totals.length,
                      volume: totals.volume, difficulty: totals.difficulty,
                      effort: totals.effort, time: totals.timeSeconds, riskScore: totals.riskScore) + "\n"

    return output
}

func formatAsSummary(_ fileMetrics: [HalsteadMetrics], totals: HalsteadMetrics, verbose: Bool) -> String {
    var output = ""

    // Health status
    let healthStatus = getHealthStatus(totals: totals, fileCount: fileMetrics.count)
    output += """

┌─ Code Health ─────────────────────────────────────────────┐
│  Status: \(healthStatus)
│  \(String(format: "%.1f", totals.riskScore)) risk score across \(fileMetrics.count) files
│  \(fileMetrics.filter { $0.riskScore > 2.0 }.count) files need attention
└───────────────────────────────────────────────────────────┘

"""

    if verbose {
        // Show all files
        output += "All Files\n\n"
        for metrics in fileMetrics.sorted(by: { $0.riskScore > $1.riskScore }) {
            output += formatFileLine(metrics)
        }
    } else {
        // Top 5 worst files
        let topWorst = fileMetrics.sorted(by: { $0.riskScore > $1.riskScore }).prefix(5)
        if !topWorst.isEmpty {
            output += "⚠️  Files Needing Attention\n\n"
            for (index, metrics) in topWorst.enumerated() {
                output += "  \(index + 1). \(shortPath(metrics.path))\n"
                output += "     \(String(format: "%.2f", metrics.riskScore)) risk • Difficulty \(String(format: "%.1f", metrics.difficulty)) (\(difficultyLabel(metrics.difficulty)))\n"
                output += "     → \(recommendation(for: metrics))\n\n"
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

    // Totals
    output += "────────────────────────────────────────────────────────────\n"
    output += "Totals: \(totals.vocabulary) vocabulary, \(String(format: "%.1f", totals.riskScore)) risk score\n"
    if !verbose {
        output += "\nRun `hal --verbose` to see all \(fileMetrics.count) files\n"
        output += "Run `hal --explain` to understand metrics\n"
    }

    return output
}

func getHealthStatus(totals: HalsteadMetrics, fileCount: Int) -> String {
    let avgRisk = totals.riskScore / Double(fileCount)
    if avgRisk < 0.5 { return "Excellent ✓" }
    if avgRisk < 1.0 { return "Good" }
    if avgRisk < 2.0 { return "Fair" }
    return "Needs Work"
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

func formatFileLine(_ metrics: HalsteadMetrics) -> String {
    return "  \(shortPath(metrics.path))\n" +
           "     Risk: \(String(format: "%.2f", metrics.riskScore)) • " +
           "Difficulty: \(String(format: "%.1f", metrics.difficulty))\n\n"
}

func recommendation(for metrics: HalsteadMetrics) -> String {
    if metrics.riskScore > 5.0 {
        return "Strong refactoring candidate - consider splitting"
    }
    if metrics.difficulty > 60 {
        return "Very complex logic - extra testing recommended"
    }
    if metrics.riskScore > 3.0 {
        return "Consider extracting sub-components"
    }
    return "Review for potential simplification"
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
            // Unknown flag or positional argument
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
        --include-tests           Include Tests directories
        --explain                 Show detailed explanation of metrics
        --help, -h                Show this help message

    EXAMPLES:
        hal --path ./Sources --format json > halstead.json
        hal --path . --format table
        hal --path . --threshold 'volume>800,difficulty>25'
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

            let swiftFiles = findSwiftFiles(at: rootURL, fileManager: fileManager)
            let calculator = MetricsCalculator()

            if options.format != .summary {
                print("Analyzing \(swiftFiles.count) Swift files...")
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
    static func findSwiftFiles(at rootURL: URL, fileManager: FileManager) -> [URL] {
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
                    swiftFiles.append(fileURL)
                }
            } catch {
                print("Error processing file attributes for \(fileURL.path): \(error)")
            }
        }
        return swiftFiles
    }
}

