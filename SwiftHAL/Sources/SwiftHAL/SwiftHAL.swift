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

    // Readability patterns (Phase 1)
    var nesting: NestingMetrics?
    var conditionals: ConditionalMetrics?
    var liveness: LivenessMetrics?
    var grouping: GroupingMetrics?

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
        case nesting, conditionals, liveness, grouping
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
        try container.encodeIfPresent(nesting, forKey: .nesting)
        try container.encodeIfPresent(conditionals, forKey: .conditionals)
        try container.encodeIfPresent(liveness, forKey: .liveness)
        try container.encodeIfPresent(grouping, forKey: .grouping)
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        path = try container.decode(String.self, forKey: .path)
        n1 = try container.decode(Int.self, forKey: .n1)
        n2 = try container.decode(Int.self, forKey: .n2)
        N1 = try container.decode(Int.self, forKey: .N1)
        N2 = try container.decode(Int.self, forKey: .N2)
        nesting = try container.decodeIfPresent(NestingMetrics.self, forKey: .nesting)
        conditionals = try container.decodeIfPresent(ConditionalMetrics.self, forKey: .conditionals)
        liveness = try container.decodeIfPresent(LivenessMetrics.self, forKey: .liveness)
        grouping = try container.decodeIfPresent(GroupingMetrics.self, forKey: .grouping)
        // Computed properties are automatically calculated from stored properties
    }
}

// MARK: - Readability Pattern: Nesting Depth

struct NestingLocation: Codable {
    let line: Int
    let column: Int
    let depth: Int
    let context: String
}

struct NestingMetrics: Codable {
    let maxDepth: Int
    let avgDepth: Double
    let deeplyNestedCount: Int  // blocks with depth > 3
    let locations: [NestingLocation]

    static var empty: NestingMetrics {
        NestingMetrics(maxDepth: 0, avgDepth: 0.0, deeplyNestedCount: 0, locations: [])
    }
}

class NestingAnalyzer: SyntaxVisitor {
    private var currentDepth = 0
    private var maxDepth = 0
    private var depthSamples: [Int] = []
    private var locations: [NestingLocation] = []
    private let converter: SourceLocationConverter

    init(viewMode: SyntaxTreeViewMode, converter: SourceLocationConverter) {
        self.converter = converter
        super.init(viewMode: viewMode)
    }

    override func visit(_ node: CodeBlockSyntax) -> SyntaxVisitorContinueKind {
        currentDepth += 1
        maxDepth = max(maxDepth, currentDepth)
        depthSamples.append(currentDepth)

        if currentDepth > 3 {
            let location = converter.location(for: node.positionAfterSkippingLeadingTrivia)
            locations.append(NestingLocation(
                line: location.line,
                column: location.column,
                depth: currentDepth,
                context: extractContext(node)
            ))
        }

        return .visitChildren
    }

    override func visitPost(_ node: CodeBlockSyntax) {
        currentDepth -= 1
    }

    private func extractContext(_ node: CodeBlockSyntax) -> String {
        // Walk up the tree to find context
        var contexts: [String] = []
        var current: Syntax? = Syntax(node)

        while let parent = current?.parent {
            if parent.is(FunctionDeclSyntax.self) {
                contexts.append("func")
            } else if parent.is(IfExprSyntax.self) {
                contexts.append("if")
            } else if parent.is(ForStmtSyntax.self) {
                contexts.append("for")
            } else if parent.is(WhileStmtSyntax.self) {
                contexts.append("while")
            } else if parent.is(SwitchExprSyntax.self) {
                contexts.append("switch")
            } else if parent.is(GuardStmtSyntax.self) {
                contexts.append("guard")
            } else if parent.is(ClosureExprSyntax.self) {
                contexts.append("closure")
            }
            current = parent
        }

        return contexts.reversed().joined(separator: "→")
    }

    func calculateMetrics() -> NestingMetrics {
        let avgDepth = depthSamples.isEmpty ? 0.0 : Double(depthSamples.reduce(0, +)) / Double(depthSamples.count)
        let deeplyNested = locations.count

        // Sort by depth descending, then by line
        let sortedLocations = locations.sorted { lhs, rhs in
            if lhs.depth != rhs.depth {
                return lhs.depth > rhs.depth
            }
            return lhs.line < rhs.line
        }

        // Keep only top 10 worst locations
        let topLocations = Array(sortedLocations.prefix(10))

        return NestingMetrics(
            maxDepth: maxDepth,
            avgDepth: avgDepth,
            deeplyNestedCount: deeplyNested,
            locations: topLocations
        )
    }
}

// MARK: - Readability Pattern: Conditional Simplicity

struct ConditionalLocation: Codable {
    let line: Int
    let column: Int
    let operatorCount: Int
    let hasMixedOperators: Bool
    let snippet: String
}

struct ConditionalMetrics: Codable {
    let totalConditionals: Int
    let complexConditionalsCount: Int  // > 6 operators
    let avgOperatorsPerCondition: Double
    let mixedOperatorCount: Int
    let locations: [ConditionalLocation]

    static var empty: ConditionalMetrics {
        ConditionalMetrics(
            totalConditionals: 0,
            complexConditionalsCount: 0,
            avgOperatorsPerCondition: 0.0,
            mixedOperatorCount: 0,
            locations: []
        )
    }
}

class ConditionalAnalyzer: SyntaxVisitor {
    private var conditionals: [ConditionalLocation] = []
    private let converter: SourceLocationConverter

    init(viewMode: SyntaxTreeViewMode, converter: SourceLocationConverter) {
        self.converter = converter
        super.init(viewMode: viewMode)
    }

    override func visit(_ node: IfExprSyntax) -> SyntaxVisitorContinueKind {
        analyzeConditions(node.conditions, context: "if", position: node.positionAfterSkippingLeadingTrivia)
        return .visitChildren
    }

    override func visit(_ node: GuardStmtSyntax) -> SyntaxVisitorContinueKind {
        analyzeConditions(node.conditions, context: "guard", position: node.positionAfterSkippingLeadingTrivia)
        return .visitChildren
    }

    override func visit(_ node: WhileStmtSyntax) -> SyntaxVisitorContinueKind {
        analyzeConditions(node.conditions, context: "while", position: node.positionAfterSkippingLeadingTrivia)
        return .visitChildren
    }

    private func analyzeConditions(_ conditions: ConditionElementListSyntax, context: String, position: AbsolutePosition) {
        var operatorCount = 0
        var hasAnd = false
        var hasOr = false

        // Count operators in the condition
        for token in conditions.tokens(viewMode: .sourceAccurate) {
            switch token.tokenKind {
            case .binaryOperator(let op):
                if op == "&&" {
                    operatorCount += 1
                    hasAnd = true
                } else if op == "||" {
                    operatorCount += 1
                    hasOr = true
                } else {
                    operatorCount += 1
                }
            // `<`, `>` and `=` in conditions are generic brackets and `if let` bindings, not operators
            case .exclamationMark:
                operatorCount += 1
            default:
                break
            }
        }

        let snippet = String(conditions.description.prefix(60))
            .trimmingCharacters(in: .whitespacesAndNewlines)

        let location = converter.location(for: position)
        conditionals.append(ConditionalLocation(
            line: location.line,
            column: location.column,
            operatorCount: operatorCount,
            hasMixedOperators: hasAnd && hasOr,
            snippet: snippet
        ))
    }

    func calculateMetrics() -> ConditionalMetrics {
        let totalCount = conditionals.count
        let complexCount = conditionals.filter { $0.operatorCount > 6 }.count
        let mixedCount = conditionals.filter { $0.hasMixedOperators }.count

        let avgOperators = totalCount > 0
            ? Double(conditionals.map { $0.operatorCount }.reduce(0, +)) / Double(totalCount)
            : 0.0

        // Report only notable conditions: more than 3 operators or mixed &&/||
        let notable = conditionals.filter { $0.operatorCount > 3 || $0.hasMixedOperators }
        let sortedLocations = notable.sorted { lhs, rhs in
            if lhs.operatorCount != rhs.operatorCount {
                return lhs.operatorCount > rhs.operatorCount
            }
            return lhs.line < rhs.line
        }

        // Keep top 10
        let topLocations = Array(sortedLocations.prefix(10))

        return ConditionalMetrics(
            totalConditionals: totalCount,
            complexConditionalsCount: complexCount,
            avgOperatorsPerCondition: avgOperators,
            mixedOperatorCount: mixedCount,
            locations: topLocations
        )
    }
}

// MARK: - Readability Pattern: Variable Liveness

struct LivenessLocation: Codable {
    let variableName: String
    let declLine: Int
    let lastUseLine: Int
    let lifespan: Int
}

struct LivenessMetrics: Codable {
    let avgLifespan: Double
    let maxLifespan: Int
    let longLivedCount: Int  // variables with lifespan > 20 lines
    let locations: [LivenessLocation]

    static var empty: LivenessMetrics {
        LivenessMetrics(
            avgLifespan: 0.0,
            maxLifespan: 0,
            longLivedCount: 0,
            locations: []
        )
    }
}

class LivenessAnalyzer: SyntaxVisitor {
    private struct VariableInfo {
        var declLine: Int
        var lastUseLine: Int
    }

    // One scope per enclosing function, so same-named locals in different functions stay separate
    private var scopes: [[String: VariableInfo]] = []
    private var finished: [(name: String, info: VariableInfo)] = []
    private let converter: SourceLocationConverter

    init(viewMode: SyntaxTreeViewMode, converter: SourceLocationConverter) {
        self.converter = converter
        super.init(viewMode: viewMode)
    }

    override func visit(_ node: FunctionDeclSyntax) -> SyntaxVisitorContinueKind {
        scopes.append([:])
        return .visitChildren
    }

    override func visitPost(_ node: FunctionDeclSyntax) {
        guard let scope = scopes.popLast() else { return }
        finished.append(contentsOf: scope.map { (name: $0.key, info: $0.value) })
    }

    override func visit(_ node: VariableDeclSyntax) -> SyntaxVisitorContinueKind {
        // Only track variables inside functions
        guard !scopes.isEmpty else { return .visitChildren }

        for binding in node.bindings {
            if let identifier = binding.pattern.as(IdentifierPatternSyntax.self) {
                let varName = identifier.identifier.text
                let line = converter.location(for: node.positionAfterSkippingLeadingTrivia).line

                // Record the first declaration in this function
                if scopes[scopes.count - 1][varName] == nil {
                    scopes[scopes.count - 1][varName] = VariableInfo(declLine: line, lastUseLine: line)
                }
            }
        }
        return .visitChildren
    }

    override func visit(_ node: DeclReferenceExprSyntax) -> SyntaxVisitorContinueKind {
        // Track usage against the innermost function that declares the name
        let varName = node.baseName.text
        if let index = scopes.lastIndex(where: { $0[varName] != nil }) {
            let location = converter.location(for: node.positionAfterSkippingLeadingTrivia)
            scopes[index][varName]?.lastUseLine = location.line
        }

        return .visitChildren
    }

    func calculateMetrics() -> LivenessMetrics {
        var lifespans: [Int] = []
        var locations: [LivenessLocation] = []

        for (name, info) in finished {
            let lifespan = info.lastUseLine - info.declLine
            lifespans.append(lifespan)

            if lifespan > 20 {
                locations.append(LivenessLocation(
                    variableName: name,
                    declLine: info.declLine,
                    lastUseLine: info.lastUseLine,
                    lifespan: lifespan
                ))
            }
        }

        let avgLifespan = lifespans.isEmpty ? 0.0 : Double(lifespans.reduce(0, +)) / Double(lifespans.count)
        let maxLifespan = lifespans.max() ?? 0

        // Sort by lifespan descending
        let sortedLocations = locations.sorted { $0.lifespan > $1.lifespan }

        // Keep top 10
        let topLocations = Array(sortedLocations.prefix(10))

        return LivenessMetrics(
            avgLifespan: avgLifespan,
            maxLifespan: maxLifespan,
            longLivedCount: locations.count,
            locations: topLocations
        )
    }
}

// MARK: - Readability Pattern: Grouping (Method Chains)

struct ChainLocation: Codable {
    let line: Int
    let column: Int
    let chainLength: Int
    let snippet: String
}

struct GroupingMetrics: Codable {
    let maxChainLength: Int
    let avgChainLength: Double
    let longChainsCount: Int  // chains > 5 calls
    let maxClosureDepth: Int
    let locations: [ChainLocation]

    static var empty: GroupingMetrics {
        GroupingMetrics(
            maxChainLength: 0,
            avgChainLength: 0.0,
            longChainsCount: 0,
            maxClosureDepth: 0,
            locations: []
        )
    }
}

class GroupingAnalyzer: SyntaxVisitor {
    private var chains: [ChainLocation] = []
    private var closureDepth = 0
    private var maxClosureDepth = 0
    private let converter: SourceLocationConverter

    init(viewMode: SyntaxTreeViewMode, converter: SourceLocationConverter) {
        self.converter = converter
        super.init(viewMode: viewMode)
    }

    override func visit(_ node: MemberAccessExprSyntax) -> SyntaxVisitorContinueKind {
        // Only count from the root of the chain (to avoid counting each link)
        guard !isPartOfLongerChain(node) else { return .visitChildren }

        // Count chain length by walking up the tree
        let chainLength = countChainLength(node)

        if chainLength > 3 {
            let location = converter.location(for: node.positionAfterSkippingLeadingTrivia)
            let rootLine = location.line

            let snippet = String(node.description.prefix(60))
                .trimmingCharacters(in: .whitespacesAndNewlines)

            chains.append(ChainLocation(
                line: rootLine,
                column: location.column,
                chainLength: chainLength,
                snippet: snippet
            ))
        }

        return .visitChildren
    }

    override func visit(_ node: ClosureExprSyntax) -> SyntaxVisitorContinueKind {
        closureDepth += 1
        maxClosureDepth = max(maxClosureDepth, closureDepth)
        return .visitChildren
    }

    override func visitPost(_ node: ClosureExprSyntax) {
        closureDepth -= 1
    }

    private func isPartOfLongerChain(_ node: MemberAccessExprSyntax) -> Bool {
        // Check if this node's parent is also a member access (indicating we're in the middle of a chain)
        var current: Syntax? = Syntax(node).parent
        while let parent = current {
            if parent.is(MemberAccessExprSyntax.self) {
                return true
            }
            // Stop at expression boundaries
            if parent.is(FunctionCallExprSyntax.self) {
                current = parent.parent
            } else {
                break
            }
        }
        return false
    }

    /// Counts member-access hops: `a.b().c.d()` is 3.
    private func countChainLength(_ node: MemberAccessExprSyntax) -> Int {
        var count = 0
        var current: Syntax? = Syntax(node)

        while let syntax = current {
            if let memberAccess = syntax.as(MemberAccessExprSyntax.self) {
                count += 1
                current = memberAccess.base.map { Syntax($0) }
            } else if let functionCall = syntax.as(FunctionCallExprSyntax.self) {
                // A call is not a hop; walk through to the member access it wraps
                current = Syntax(functionCall.calledExpression)
            } else {
                break
            }
        }

        return count
    }

    func calculateMetrics() -> GroupingMetrics {
        let maxChain = chains.map { $0.chainLength }.max() ?? 0
        let avgChain = chains.isEmpty ? 0.0 : Double(chains.map { $0.chainLength }.reduce(0, +)) / Double(chains.count)
        let longChains = chains.filter { $0.chainLength > 5 }.count

        // Sort by chain length descending
        let sortedLocations = chains.sorted { lhs, rhs in
            if lhs.chainLength != rhs.chainLength {
                return lhs.chainLength > rhs.chainLength
            }
            return lhs.line < rhs.line
        }

        // Keep top 10
        let topLocations = Array(sortedLocations.prefix(10))

        return GroupingMetrics(
            maxChainLength: maxChain,
            avgChainLength: avgChain,
            longChainsCount: longChains,
            maxClosureDepth: maxClosureDepth,
            locations: topLocations
        )
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
        if let key = MetricKey.allCases.first(where: { $0.rawValue.lowercased() == normalized }) {
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

        case .keyword(.`init`), .keyword(.deinit), .keyword(.subscript), .keyword(.extension),
             .keyword(.typealias), .keyword(.associatedtype), .keyword(.actor), .keyword(.operator),
             .keyword(.fallthrough), .keyword(.static), .keyword(.inout), .keyword(.async),
             .keyword(.await), .keyword(.some), .keyword(.any), .keyword(.mutating),
             .keyword(.override), .keyword(.private), .keyword(.fileprivate), .keyword(.internal),
             .keyword(.public), .keyword(.open), .keyword(.final), .keyword(.lazy),
             .keyword(.weak), .keyword(.unowned), .keyword(.get), .keyword(.set),
             .keyword(.willSet), .keyword(.didSet):
            return .operator

        // MARK: Operands

        // Identifiers
        case .identifier(_), .dollarIdentifier(_):
            return .operand

        // Self references
        case .keyword(.`self`), .keyword(.`Self`), .keyword(.`super`):
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

    /// Distinct-operand key. Literals are prefixed by kind so the string "1" and the integer 1 count as different operands.
    static func operandKey(_ token: TokenSyntax) -> String {
        switch token.tokenKind {
        case .integerLiteral(_): return "int:" + token.text
        case .floatLiteral(_): return "float:" + token.text
        case .stringSegment(_): return "str:" + token.text
        case .regexLiteralPattern(_): return "regex:" + token.text
        default: return token.text
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
            switch TokenClassifier.classify(token) {
            case .operator:
                metrics.N1 += 1
                distinctOperators.insert(token.text)
            case .operand:
                metrics.N2 += 1
                distinctOperands.insert(TokenClassifier.operandKey(token))
            case .ignored:
                continue
            }
        }

        metrics.n1 = distinctOperators.count
        metrics.n2 = distinctOperands.count

        // Create source location converter for line/column information
        let converter = SourceLocationConverter(fileName: fileURL.path, tree: tree)

        // Run readability pattern analyzers
        let nestingAnalyzer = NestingAnalyzer(viewMode: .sourceAccurate, converter: converter)
        nestingAnalyzer.walk(tree)
        metrics.nesting = nestingAnalyzer.calculateMetrics()

        let conditionalAnalyzer = ConditionalAnalyzer(viewMode: .sourceAccurate, converter: converter)
        conditionalAnalyzer.walk(tree)
        metrics.conditionals = conditionalAnalyzer.calculateMetrics()

        let livenessAnalyzer = LivenessAnalyzer(viewMode: .sourceAccurate, converter: converter)
        livenessAnalyzer.walk(tree)
        metrics.liveness = livenessAnalyzer.calculateMetrics()

        let groupingAnalyzer = GroupingAnalyzer(viewMode: .sourceAccurate, converter: converter)
        groupingAnalyzer.walk(tree)
        metrics.grouping = groupingAnalyzer.calculateMetrics()

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

            guard MetricKey(string: metric) != nil, let value = Double(valueString) else {
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

        // A threshold names the failing condition: "volume>800" fails when volume is over 800.
        if compareValues(actualValue, threshold.comparator, threshold.value) {
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

/// Extracts the first folder under `root` from a file path.
/// Examples (root "/Users/foo/project"):
/// - /Users/foo/project/App/Views/File.swift -> App/
/// - /Users/foo/project/main.swift -> .
/// With an empty root the path is treated as already relative (App/Views/File.swift -> App/).
func extractDirectory(from path: String, root: String = "") -> String {
    var relative = path
    if !root.isEmpty {
        let prefix = root.hasSuffix("/") ? root : root + "/"
        if relative.hasPrefix(prefix) {
            relative = String(relative.dropFirst(prefix.count))
        }
    }
    let components = relative.split(separator: "/")
    return components.count > 1 ? String(components[0]) + "/" : "."
}

func groupByDirectory(_ fileMetrics: [HalsteadMetrics], root: String = "") -> [String: [HalsteadMetrics]] {
    var grouped: [String: [HalsteadMetrics]] = [:]

    for metrics in fileMetrics {
        let directory = extractDirectory(from: metrics.path, root: root)

        if grouped[directory] == nil {
            grouped[directory] = []
        }
        grouped[directory]?.append(metrics)
    }

    return grouped
}

func formatArchitectureHotspots(_ fileMetrics: [HalsteadMetrics], root: String = "") -> String {
    var output = ""

    output += """

ARCHITECTURE HOTSPOTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

    let grouped = groupByDirectory(fileMetrics, root: root)

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

func pad(_ string: String, to width: Int, rightAlign: Bool = false) -> String {
    if string.count >= width { return string }
    let padding = String(repeating: " ", count: width - string.count)
    return rightAlign ? padding + string : string + padding
}

func formatAsTable(_ fileMetrics: [HalsteadMetrics], totals: HalsteadMetrics) -> String {
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

func formatNestingAnalysis(_ fileMetrics: [HalsteadMetrics]) -> String {
    // Aggregate nesting stats across all files
    let filesWithNesting = fileMetrics.compactMap { $0.nesting }
    guard !filesWithNesting.isEmpty else { return "" }

    let maxDepthOverall = filesWithNesting.map { $0.maxDepth }.max() ?? 0
    let avgDepthOverall = filesWithNesting.map { $0.avgDepth }.reduce(0.0, +) / Double(filesWithNesting.count)
    let deeplyNestedTotal = filesWithNesting.map { $0.deeplyNestedCount }.reduce(0, +)

    // Categorize files by max depth
    let critical = filesWithNesting.filter { $0.maxDepth >= 8 }.count
    let high = filesWithNesting.filter { $0.maxDepth >= 6 && $0.maxDepth < 8 }.count
    let moderate = filesWithNesting.filter { $0.maxDepth >= 4 && $0.maxDepth < 6 }.count
    let low = filesWithNesting.filter { $0.maxDepth < 4 }.count

    var output = "\nNESTING COMPLEXITY\n"
    output += String(repeating: "━", count: 62) + "\n"
    output += "Project: Max depth \(maxDepthOverall) │ Avg \(String(format: "%.1f", avgDepthOverall)) │ \(deeplyNestedTotal) deeply nested blocks\n\n"

    // File categories
    if critical > 0 {
        output += "🔴 Critical (≥8): \(critical) file\(critical == 1 ? "" : "s")\n"
    }
    if high > 0 {
        output += "🟡 High (6-7): \(high) file\(high == 1 ? "" : "s")\n"
    }
    if moderate > 0 {
        output += "🟠 Moderate (4-5): \(moderate) file\(moderate == 1 ? "" : "s")\n"
    }
    if low > 0 {
        output += "🟢 Low (≤3): \(low) file\(low == 1 ? "" : "s")\n"
    }

    // Show worst files with deep nesting
    let worstFiles = fileMetrics
        .filter { ($0.nesting?.deeplyNestedCount ?? 0) > 0 }
        .sorted { ($0.nesting?.maxDepth ?? 0) > ($1.nesting?.maxDepth ?? 0) }
        .prefix(5)

    if !worstFiles.isEmpty {
        output += "\n⚠️  Files with Deep Nesting:\n"
        for metrics in worstFiles {
            guard let nesting = metrics.nesting else { continue }
            output += "  \(shortPath(metrics.path))\n"
            output += "  └─ Max depth: \(nesting.maxDepth) │ Avg: \(String(format: "%.1f", nesting.avgDepth)) │ \(nesting.deeplyNestedCount) deep blocks\n"

            // Show top 3 worst locations in this file
            for location in nesting.locations.prefix(3) {
                output += "     Line \(location.line): \(location.depth) levels (\(location.context))\n"
            }
            output += "\n"
        }
    }

    return output
}

func formatConditionalAnalysis(_ fileMetrics: [HalsteadMetrics]) -> String {
    // Aggregate conditional stats across all files
    let filesWithConditionals = fileMetrics.compactMap { $0.conditionals }
    guard !filesWithConditionals.isEmpty else { return "" }

    let totalConditionals = filesWithConditionals.map { $0.totalConditionals }.reduce(0, +)
    let complexTotal = filesWithConditionals.map { $0.complexConditionalsCount }.reduce(0, +)
    let mixedTotal = filesWithConditionals.map { $0.mixedOperatorCount }.reduce(0, +)

    let avgOperators = totalConditionals > 0
        ? filesWithConditionals.map { $0.avgOperatorsPerCondition * Double($0.totalConditionals) }.reduce(0.0, +) / Double(totalConditionals)
        : 0.0

    var output = "\nCONDITIONAL COMPLEXITY\n"
    output += String(repeating: "━", count: 62) + "\n"
    output += "Project: \(totalConditionals) conditionals │ Avg \(String(format: "%.1f", avgOperators)) operators │ \(complexTotal) complex (>6 ops)\n"

    if mixedTotal > 0 {
        output += "⚠️  \(mixedTotal) conditional\(mixedTotal == 1 ? "" : "s") with mixed &&/|| operators\n"
    }

    // Show worst files with complex conditionals
    let worstFiles = fileMetrics
        .filter { ($0.conditionals?.complexConditionalsCount ?? 0) > 0 || ($0.conditionals?.mixedOperatorCount ?? 0) > 0 }
        .sorted { lhs, rhs in
            let lhsWorst = lhs.conditionals?.locations.first?.operatorCount ?? 0
            let rhsWorst = rhs.conditionals?.locations.first?.operatorCount ?? 0
            return lhsWorst > rhsWorst
        }
        .prefix(5)

    if !worstFiles.isEmpty {
        output += "\n⚠️  Complex Conditionals:\n"
        for metrics in worstFiles {
            guard let conditionals = metrics.conditionals else { continue }

            output += "  \(shortPath(metrics.path))\n"

            // Show top 3 worst conditionals in this file
            for location in conditionals.locations.prefix(3) {
                let mixedWarning = location.hasMixedOperators ? " ⚠️ mixed &&/||" : ""
                output += "  └─ Line \(location.line): \(location.operatorCount) operators\(mixedWarning)\n"
                output += "     \(location.snippet)\n"
            }
            output += "\n"
        }
    }

    return output
}

func formatLivenessAnalysis(_ fileMetrics: [HalsteadMetrics]) -> String {
    // Aggregate liveness stats across all files
    let filesWithLiveness = fileMetrics.compactMap { $0.liveness }
    guard !filesWithLiveness.isEmpty else { return "" }

    let avgLifespanOverall = filesWithLiveness.map { $0.avgLifespan }.reduce(0.0, +) / Double(filesWithLiveness.count)
    let maxLifespanOverall = filesWithLiveness.map { $0.maxLifespan }.max() ?? 0
    let longLivedTotal = filesWithLiveness.map { $0.longLivedCount }.reduce(0, +)

    guard longLivedTotal > 0 else { return "" }  // Only show if there are long-lived variables

    var output = "\nVARIABLE LIVENESS\n"
    output += String(repeating: "━", count: 62) + "\n"
    output += "Project: Max span \(maxLifespanOverall) lines │ Avg \(String(format: "%.1f", avgLifespanOverall)) lines │ \(longLivedTotal) long-lived (>20 lines)\n"

    // Show files with long-lived variables
    let worstFiles = fileMetrics
        .filter { ($0.liveness?.longLivedCount ?? 0) > 0 }
        .sorted { ($0.liveness?.maxLifespan ?? 0) > ($1.liveness?.maxLifespan ?? 0) }
        .prefix(5)

    if !worstFiles.isEmpty {
        output += "\n⚠️  Long-Lived Variables:\n"
        for metrics in worstFiles {
            guard let liveness = metrics.liveness else { continue }

            output += "  \(shortPath(metrics.path))\n"

            // Show top 3 worst variables in this file
            for location in liveness.locations.prefix(3) {
                output += "  └─ '\(location.variableName)' (lines \(location.declLine)-\(location.lastUseLine)): \(location.lifespan) lines\n"
            }
            output += "\n"
        }

        output += "  💡 Tip: Move variable declarations closer to first use\n"
    }

    return output
}

func formatGroupingAnalysis(_ fileMetrics: [HalsteadMetrics]) -> String {
    // Aggregate grouping stats across all files
    let filesWithGrouping = fileMetrics.compactMap { $0.grouping }
    guard !filesWithGrouping.isEmpty else { return "" }

    let maxChainOverall = filesWithGrouping.map { $0.maxChainLength }.max() ?? 0
    let longChainsTotal = filesWithGrouping.map { $0.longChainsCount }.reduce(0, +)
    let maxClosureDepth = filesWithGrouping.map { $0.maxClosureDepth }.max() ?? 0

    guard longChainsTotal > 0 || maxClosureDepth > 2 else { return "" }  // Only show if there are issues

    var output = "\nMETHOD CHAINING & GROUPING\n"
    output += String(repeating: "━", count: 62) + "\n"
    output += "Project: Max chain \(maxChainOverall) calls │ \(longChainsTotal) long chains (>5 calls)"

    if maxClosureDepth > 2 {
        output += " │ Max closure depth \(maxClosureDepth)"
    }
    output += "\n"

    // Show files with long chains
    let worstFiles = fileMetrics
        .filter { ($0.grouping?.longChainsCount ?? 0) > 0 }
        .sorted { ($0.grouping?.maxChainLength ?? 0) > ($1.grouping?.maxChainLength ?? 0) }
        .prefix(5)

    if !worstFiles.isEmpty {
        output += "\n⚠️  Long Method Chains:\n"
        for metrics in worstFiles {
            guard let grouping = metrics.grouping else { continue }

            output += "  \(shortPath(metrics.path))\n"

            // Show top 3 longest chains in this file
            for location in grouping.locations.prefix(3) {
                output += "  └─ Line \(location.line): \(location.chainLength) chained calls\n"
                output += "     \(location.snippet)...\n"
            }
            output += "\n"
        }

        output += "  💡 Tip: Break long chains with intermediate variables\n"
    }

    return output
}

func formatProjectSummary(avgRisk: Double, medianRisk: Double, maxRisk: Double, vocabulary: Int, needsAttentionCount: Int, needsAttentionPct: Int, focusAreas: [String]) -> String {
    var output = "────────────────────────────────────────────────────────────\n"
    output += "📊 PROJECT SUMMARY\n\n"
    output += "  Complexity    \(String(format: "%.2f", avgRisk)) avg  │  \(String(format: "%.2f", medianRisk)) median  │  \(String(format: "%.2f", maxRisk)) max\n"
    output += "  Vocabulary    \(formatWithThousandsSeparator(vocabulary)) distinct symbols\n"
    output += "  Health        \(needsAttentionCount) files need attention (\(needsAttentionPct)% of codebase)\n"
    if !focusAreas.isEmpty {
        output += "  Focus Areas   \(focusAreas.joined(separator: ", "))\n"
    }
    return output
}

/// Mean of per-file risk scores. The totals' risk is computed over the merged vocabulary, so dividing it by the file count is not an average.
func averageRisk(_ fileMetrics: [HalsteadMetrics]) -> Double {
    guard !fileMetrics.isEmpty else { return 0.0 }
    return fileMetrics.reduce(0.0) { $0 + $1.riskScore } / Double(fileMetrics.count)
}

func formatAsSummary(_ fileMetrics: [HalsteadMetrics], totals: HalsteadMetrics, verbose: Bool, root: String = "") -> String {
    var output = ""

    // Files needing attention: risk >= moderate (for count), but display only >= high
    let filesNeedingAttention = fileMetrics.filter { $0.riskScore >= RiskThresholds.moderate }
    let criticalAndHighFiles = fileMetrics.filter { $0.riskScore >= RiskThresholds.high }
    let needsAttentionCount = filesNeedingAttention.count
    let needsAttentionText = needsAttentionCount == 1 ? "1 file needs attention" : "\(needsAttentionCount) files need attention"
    let projectAvg = averageRisk(fileMetrics)

    // Header
    output += formatSummaryHeader(fileCount: fileMetrics.count, projectAvg: projectAvg, needsAttentionText: needsAttentionText)

    // Risk distribution and architecture hotspots
    output += "\n" + formatRiskDistribution(fileMetrics) + "\n"
    output += formatArchitectureHotspots(fileMetrics, root: root) + "\n"

    // Readability patterns
    output += formatNestingAnalysis(fileMetrics)
    output += formatConditionalAnalysis(fileMetrics)
    output += formatLivenessAnalysis(fileMetrics)
    output += formatGroupingAnalysis(fileMetrics)

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
    let medianRisk = calculateMedianRisk(fileMetrics)
    let maxRisk = calculateMaxRisk(fileMetrics)
    let focusAreas = extractFocusAreas(fileMetrics, root: root)
    let needsAttentionPct = filesNeedingAttention.count * 100 / fileMetrics.count

    output += formatProjectSummary(
        avgRisk: projectAvg,
        medianRisk: medianRisk,
        maxRisk: maxRisk,
        vocabulary: totals.vocabulary,
        needsAttentionCount: needsAttentionCount,
        needsAttentionPct: needsAttentionPct,
        focusAreas: focusAreas
    )

    return output
}

func getHealthStatus(_ fileMetrics: [HalsteadMetrics]) -> String {
    let avgRisk = averageRisk(fileMetrics)
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

func extractFocusAreas(_ fileMetrics: [HalsteadMetrics], root: String = "") -> [String] {
    let high_risk_files = fileMetrics.filter { $0.riskScore >= RiskThresholds.high }
    var directories = Set<String>()

    for metrics in high_risk_files {
        let directory = extractDirectory(from: metrics.path, root: root)

        if directory != "." {
            directories.insert(directory)
        }
    }

    return Array(directories).sorted()
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
    var verbose: Bool = false
}

enum CLIError: Error {
    case invalid_threshold(String)
}

func printError(_ message: String) {
    FileHandle.standardError.write(Data((message + "\n").utf8))
}

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

    var path: String {
        return pathOption ?? pathArgument ?? "."
    }

    @Option(name: .long, help: "Output format: json, table, summary")
    var format: OutputFormat = .summary

    @Option(name: .long, help: "Threshold conditions (e.g., 'volume>800,difficulty>20')")
    var threshold: String?

    @Option(name: .long, help: "Write output to file instead of stdout")
    var output: String?

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

        let options = CLIOptions(
            path: path,
            format: format,
            thresholds: threshold?.split(separator: ",").map(String.init),
            output_path: output,
            include_tests: includeTests,
            verbose: verbose
        )

        try SwiftHAL.runAnalysis(options: options)
    }

    static func runAnalysis(options: CLIOptions) throws {
        let fileManager = FileManager.default
        // realpath, not standardizedFileURL or resolvingSymlinksInPath: the enumerator yields
        // /private/tmp/... and those Foundation calls strip /private, so hotspot grouping would miss the root prefix
        let resolvedPath = realpath(options.path, nil).map { pointer -> String in
            defer { free(pointer) }
            return String(cString: pointer)
        } ?? options.path
        let rootURL = URL(fileURLWithPath: resolvedPath)

        // Validate path exists
        var isDirectory: ObjCBool = false
        guard fileManager.fileExists(atPath: rootURL.path, isDirectory: &isDirectory) else {
            printError("Error: Path does not exist: \(rootURL.path)")
            throw ExitCode.failure
        }

        // Parse thresholds before analysis so a typo fails fast
        let thresholds = try (options.thresholds ?? []).map { try parseThreshold($0) }

        // Progress goes to stderr so stdout carries only the report (e.g. valid JSON)
        if options.format != .summary {
            printError("Analyzing Swift files in: \(rootURL.path)")
        }

        let swiftFiles = findSwiftFiles(at: rootURL, options: options, fileManager: fileManager)
        guard !swiftFiles.isEmpty else {
            printError("Error: No Swift files found in \(rootURL.path)")
            throw ExitCode.failure
        }

        if options.format != .summary {
            printError("Found \(swiftFiles.count) Swift files...")
        }

        let calculator = MetricsCalculator()
        var allResults: [MetricsWithSets] = []

        for fileURL in swiftFiles {
            do {
                let result = try calculator.calculateWithSets(for: fileURL)
                allResults.append(result)

                if options.format != .summary {
                    let metrics = result.metrics
                    printError("File: \(metrics.path)")
                    printError("  Vocabulary: \(metrics.vocabulary), Length: \(metrics.length), Volume: \(String(format: "%.2f", metrics.volume))")
                    printError("  Difficulty: \(String(format: "%.2f", metrics.difficulty)), Effort: \(String(format: "%.2f", metrics.effort)), Risk Score: \(String(format: "%.2f", metrics.riskScore))")
                }
            } catch {
                printError("Error calculating metrics for \(fileURL.path): \(error)")
            }
        }

        guard !allResults.isEmpty else {
            printError("Error: No Swift files could be analyzed in \(rootURL.path)")
            throw ExitCode.failure
        }

        let totals = aggregateTotals(allResults)
        let fileMetrics = allResults.map { $0.metrics }
        let groupingRoot = isDirectory.boolValue ? rootURL.path : rootURL.deletingLastPathComponent().path

        // Generate output based on format
        let output: String
        switch options.format {
        case .summary:
            output = formatAsSummary(fileMetrics, totals: totals, verbose: options.verbose, root: groupingRoot)
        case .json:
            output = formatAsJSON(fileMetrics, totals: totals)
        case .table:
            output = formatAsTable(fileMetrics, totals: totals)
        }

        if let output_path = options.output_path {
            try output.write(toFile: output_path, atomically: true, encoding: .utf8)
            printError("Output written to \(output_path)")
        } else {
            print(output)
        }

        // Thresholds apply per file; the project totals are not a file
        let violations = fileMetrics.flatMap { checkThresholds($0, thresholds: thresholds) }
        if !violations.isEmpty {
            printError("\nThreshold violations:")
            for violation in violations {
                printError("  \(violation)")
            }
            throw ExitCode(2)
        }
    }

    /// Finds Swift files under a directory, or returns the path itself when it is a Swift file.
    static func findSwiftFiles(at rootURL: URL, options: CLIOptions, fileManager: FileManager) -> [URL] {
        var isDirectory: ObjCBool = false
        if fileManager.fileExists(atPath: rootURL.path, isDirectory: &isDirectory), !isDirectory.boolValue {
            return rootURL.pathExtension == "swift" ? [rootURL] : []
        }

        var swiftFiles: [URL] = []
        let enumerator = fileManager.enumerator(at: rootURL,
                                               includingPropertiesForKeys: [.isRegularFileKey, .isDirectoryKey],
                                               options: [.skipsHiddenFiles, .skipsPackageDescendants])

        guard let fileEnumerator = enumerator else {
            printError("Error: Could not enumerate files at \(rootURL.path)")
            return []
        }

        for case let fileURL as URL in fileEnumerator {
            do {
                let resourceValues = try fileURL.resourceValues(forKeys: [.isRegularFileKey, .isDirectoryKey])
                if resourceValues.isDirectory == true {
                    // The enumerator never yields the root, so only Tests folders below it are skipped
                    if !options.include_tests && fileURL.lastPathComponent == "Tests" {
                        fileEnumerator.skipDescendants()
                    }
                    continue
                }
                if resourceValues.isRegularFile == true && fileURL.pathExtension == "swift" {
                    // Apply exclusion filters
                    if shouldExcludeFile(fileURL, options: options) {
                        continue
                    }
                    swiftFiles.append(fileURL)
                }
            } catch {
                printError("Error processing file attributes for \(fileURL.path): \(error)")
            }
        }
        return swiftFiles
    }

    /// Determines if a file should be excluded based on CLI options.
    static func shouldExcludeFile(_ fileURL: URL, options: CLIOptions) -> Bool {
        // Always exclude Package.swift (not analyzable code)
        if fileURL.lastPathComponent == "Package.swift" {
            return true
        }

        // Exclude files ending in Tests.swift unless tests are included
        return !options.include_tests && fileURL.lastPathComponent.hasSuffix("Tests.swift")
    }
}
