# SwiftHAL Readability Patterns Enhancement TODO

## Overview

Enhance SwiftHAL with visual code readability patterns from [seeinglogic.com](https://seeinglogic.com/posts/visual-readability-patterns/) to provide refactoring guidance for developers.

**Goals (in priority order):**
1. **Developer Education** - Help developers understand code quality issues
2. **Refactoring Guidance** - Identify specific areas needing improvement
3. **CI/CD Quality Gates** - Objective metrics for build failures

**Scope**: Metrics calculated per-file/per-folder (matching analysis scope)

**Output**: New risk categories in TUI summary format

---

## Pattern Implementation Priority

### ✅ Phase 0: Already Implemented
- **Pattern 1: Line/Operator/Operand Count** - Core SwiftHAL functionality

### ✅ Phase 1: Quick Wins (High Value, Moderate Effort) - COMPLETED
1. ✅ **Pattern 6: Nesting Depth** - Implemented in v2.1
2. ✅ **Pattern 4: Conditional Simplicity** - Implemented in v2.1
3. ✅ **Pattern 8: Variable Liveness** - Implemented in v2.1
4. ✅ **Pattern 3: Grouping (Method Chains)** - Implemented in v2.1

### 📋 Phase 2: Additional Patterns (Medium Value)

**⚠️ IMPLEMENTATION ORDER REVISED**: Pattern 2 should be done first (see Critical Analysis below)

5. **Pattern 2: Novelty Detection** ⭐ RECOMMENDED FIRST
   - **Effort**: Low (4 hours)
   - **Risk**: Low
   - **Value**: Educational
   - Custom operators, advanced Swift features

6. **Pattern 7: Variable Distinction** ⚠️ COMPLEX - DO LATER
   - **Effort**: High (35-45 hours, not 19 as originally estimated)
   - **Risk**: High (false positives, performance)
   - **Value**: High IF implemented well
   - Shadowing, similar names, single-letter vars
   - Requires prototype phase and user testing

### ⏸️ Phase 3: Not Applicable
- **Pattern 5: Gotos** - Swift doesn't have goto (could flag labeled break/continue)

---

## Phase 1: Quick Wins

### 🎯 Pattern 6: Nesting Depth

**What to Detect:**
- Maximum indentation depth in functions/methods/closures
- Average nesting level per file
- Count of deeply nested blocks (>3 levels)

**Risk Thresholds:**
- 🟢 Low: max depth ≤ 3
- 🟠 Moderate: max depth 4-5
- 🟡 High: max depth 6-7
- 🔴 Critical: max depth ≥ 8

**Technical Approach:**

```swift
// New struct in SwiftHAL.swift
struct NestingMetrics: Codable {
    let maxDepth: Int
    let avgDepth: Double
    let deeplyNestedCount: Int  // blocks with depth > 3
    let locations: [NestingLocation]  // for developer guidance
}

struct NestingLocation: Codable {
    let line: Int
    let depth: Int
    let context: String  // e.g., "if inside for inside func"
}

class NestingAnalyzer: SyntaxVisitor {
    private var currentDepth = 0
    private var maxDepth = 0
    private var depthSamples: [Int] = []
    private var locations: [NestingLocation] = []

    override func visit(_ node: CodeBlockSyntax) -> SyntaxVisitorContinueKind {
        currentDepth += 1
        maxDepth = max(maxDepth, currentDepth)
        depthSamples.append(currentDepth)

        if currentDepth > 3 {
            locations.append(NestingLocation(
                line: node.position.line,
                depth: currentDepth,
                context: extractContext(node)
            ))
        }

        return .visitChildren
    }

    override func visitPost(_ node: CodeBlockSyntax) {
        currentDepth -= 1
    }
}
```

**Integration Points:**
- Add `NestingMetrics` to `HalsteadMetrics` struct (make it optional for backward compatibility)
- Call `NestingAnalyzer` in `MetricsCalculator.calculateWithSets()`
- Add nesting summary to TUI output in `formatAsSummary()`
- Create new section: "NESTING ANALYSIS" between Architecture Hotspots and Files Needing Attention

**Output Format (TUI):**
```
NESTING COMPLEXITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 Critical Nesting (≥8)     2 files
🟡 High Nesting (6-7)        5 files
🟠 Moderate Nesting (4-5)    12 files
🟢 Low Nesting (≤3)          45 files

📁 Files with Deep Nesting:
  Sources/Parser/ComplexParser.swift
  └─ Line 145: 8 levels (if→for→if→switch→case→if→guard→if)
  └─ Line 289: 7 levels (func→if→for→if→guard→if→if)
```

---

### 🎯 Pattern 4: Conditional Simplicity

**What to Detect:**
- Operator count per conditional expression
- Mixed logical operators (`&&` with `||` without grouping)
- Complex guard/if/while conditions

**Risk Thresholds:**
- 🟢 Low: ≤ 3 operators per condition
- 🟠 Moderate: 4-6 operators
- 🟡 High: 7-10 operators
- 🔴 Critical: > 10 operators

**Technical Approach:**

```swift
struct ConditionalMetrics: Codable {
    let totalConditionals: Int
    let complexConditionalsCount: Int  // > 3 operators
    let avgOperatorsPerCondition: Double
    let mixedOperatorCount: Int  // conditions with both && and ||
    let locations: [ConditionalLocation]
}

struct ConditionalLocation: Codable {
    let line: Int
    let operatorCount: Int
    let hasMixedOperators: Bool
    let snippet: String  // first 50 chars of condition
}

class ConditionalAnalyzer: SyntaxVisitor {
    private var conditionals: [ConditionalLocation] = []

    override func visit(_ node: IfExprSyntax) -> SyntaxVisitorContinueKind {
        analyzeCondition(node.conditions, context: "if")
        return .visitChildren
    }

    override func visit(_ node: GuardStmtSyntax) -> SyntaxVisitorContinueKind {
        analyzeCondition(node.conditions, context: "guard")
        return .visitChildren
    }

    override func visit(_ node: WhileStmtSyntax) -> SyntaxVisitorContinueKind {
        analyzeCondition(node.conditions, context: "while")
        return .visitChildren
    }

    private func analyzeCondition(_ conditions: ConditionElementListSyntax, context: String) {
        // Count operators in condition
        var operatorCount = 0
        var hasAnd = false
        var hasOr = false

        for token in conditions.tokens(viewMode: .sourceAccurate) {
            switch token.tokenKind {
            case .binaryOperator("&&"):
                operatorCount += 1
                hasAnd = true
            case .binaryOperator("||"):
                operatorCount += 1
                hasOr = true
            case .exclamationMark, .leftAngle, .rightAngle, .equal:
                operatorCount += 1
            default:
                break
            }
        }

        let hasMixed = hasAnd && hasOr
        let snippet = String(conditions.description.prefix(50))

        conditionals.append(ConditionalLocation(
            line: conditions.position.line,
            operatorCount: operatorCount,
            hasMixedOperators: hasMixed,
            snippet: snippet
        ))
    }
}
```

**Integration Points:**
- Add `ConditionalMetrics` to `HalsteadMetrics`
- Call `ConditionalAnalyzer` in `MetricsCalculator.calculateWithSets()`
- Add conditional complexity section to TUI

**Output Format (TUI):**
```
CONDITIONAL COMPLEXITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: 156 conditionals │ Avg: 2.3 operators │ 12 complex (>6 ops)

⚠️  Complex Conditionals:
  Sources/Logic/Validator.swift:234
  └─ 12 operators, mixed &&/|| ⚠️
  └─ if user.isActive && (role == .admin || role == ...

  Sources/Logic/Processor.swift:89
  └─ 8 operators
  └─ guard let data = input, !data.isEmpty, data.co...
```

---

### 🎯 Pattern 8: Variable Liveness

**What to Detect:**
- Lines between variable declaration and last use
- Variables declared far from usage (> 20 lines)
- Variables with "short" vs "long" lifespans

**Risk Thresholds:**
- 🟢 Low: avg lifespan ≤ 10 lines
- 🟠 Moderate: avg lifespan 11-20 lines
- 🟡 High: avg lifespan 21-40 lines
- 🔴 Critical: avg lifespan > 40 lines

**Technical Approach:**

```swift
struct LivenessMetrics: Codable {
    let avgLifespan: Double  // lines between decl and last use
    let maxLifespan: Int
    let longLivedCount: Int  // variables with lifespan > 20 lines
    let locations: [LivenessLocation]
}

struct LivenessLocation: Codable {
    let variableName: String
    let declLine: Int
    let lastUseLine: Int
    let lifespan: Int
}

class LivenessAnalyzer: SyntaxVisitor {
    private var variables: [String: VariableInfo] = [:]
    private var currentScope: [String] = []  // stack for scope tracking

    struct VariableInfo {
        var declLine: Int
        var lastUseLine: Int
        var scope: String
    }

    override func visit(_ node: VariableDeclSyntax) -> SyntaxVisitorContinueKind {
        // Record declaration
        for binding in node.bindings {
            if let identifier = binding.pattern.as(IdentifierPatternSyntax.self) {
                let varName = identifier.identifier.text
                let line = node.position.line
                variables[varName] = VariableInfo(
                    declLine: line,
                    lastUseLine: line,
                    scope: currentScope.joined(separator: ".")
                )
            }
        }
        return .visitChildren
    }

    override func visit(_ node: DeclReferenceExprSyntax) -> SyntaxVisitorContinueKind {
        // Track variable usage
        let varName = node.baseName.text
        if variables[varName] != nil {
            variables[varName]?.lastUseLine = node.position.line
        }
        return .visitChildren
    }

    override func visit(_ node: FunctionDeclSyntax) -> SyntaxVisitorContinueKind {
        currentScope.append(node.name.text)
        return .visitChildren
    }

    override func visitPost(_ node: FunctionDeclSyntax) {
        currentScope.removeLast()
    }

    func calculateMetrics() -> LivenessMetrics {
        var lifespans: [Int] = []
        var locations: [LivenessLocation] = []

        for (name, info) in variables {
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

        return LivenessMetrics(
            avgLifespan: avgLifespan,
            maxLifespan: maxLifespan,
            longLivedCount: locations.count,
            locations: locations.sorted { $0.lifespan > $1.lifespan }
        )
    }
}
```

**Integration Points:**
- Add `LivenessMetrics` to `HalsteadMetrics`
- Call `LivenessAnalyzer` in `MetricsCalculator.calculateWithSets()`
- Add liveness section to TUI

**Output Format (TUI):**
```
VARIABLE LIVENESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: Avg 8.5 lines │ Max 67 lines │ 8 long-lived variables (>20 lines)

⚠️  Long-Lived Variables:
  Sources/Core/Manager.swift
  └─ 'configuration' (lines 45-112): 67 lines ⚠️
  └─ Recommendation: Move declaration closer to first use

  Sources/Utils/Helper.swift
  └─ 'tempData' (lines 23-58): 35 lines
  └─ Recommendation: Consider splitting into smaller scope
```

---

### 🎯 Pattern 3: Grouping (Method Chains)

**What to Detect:**
- Length of chained method calls
- Nested closure depth
- Complex functional pipelines

**Risk Thresholds:**
- 🟢 Low: ≤ 3 chained calls
- 🟠 Moderate: 4-5 chained calls
- 🟡 High: 6-8 chained calls
- 🔴 Critical: > 8 chained calls

**Technical Approach:**

```swift
struct GroupingMetrics: Codable {
    let maxChainLength: Int
    let avgChainLength: Double
    let longChainsCount: Int  // chains > 5 calls
    let nestedClosureDepth: Int
    let locations: [ChainLocation]
}

struct ChainLocation: Codable {
    let line: Int
    let chainLength: Int
    let snippet: String
}

class GroupingAnalyzer: SyntaxVisitor {
    private var chains: [ChainLocation] = []
    private var closureDepth = 0
    private var maxClosureDepth = 0

    override func visit(_ node: MemberAccessExprSyntax) -> SyntaxVisitorContinueKind {
        // Count chain length by walking up the tree
        var chainLength = 1
        var current: Syntax? = Syntax(node)

        while let parent = current?.parent,
              parent.is(MemberAccessExprSyntax.self) || parent.is(FunctionCallExprSyntax.self) {
            chainLength += 1
            current = parent
        }

        if chainLength > 3 {
            chains.append(ChainLocation(
                line: node.position.line,
                chainLength: chainLength,
                snippet: String(node.description.prefix(60))
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
}
```

**Integration Points:**
- Add `GroupingMetrics` to `HalsteadMetrics`
- Call `GroupingAnalyzer` in `MetricsCalculator.calculateWithSets()`
- Add grouping section to TUI

**Output Format (TUI):**
```
METHOD CHAINING & GROUPING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: Max chain 12 calls │ Avg 2.1 calls │ 7 long chains (>5 calls)

⚠️  Long Method Chains:
  Sources/Data/Pipeline.swift:156
  └─ 12 chained calls ⚠️
  └─ data.filter { }.map { }.compactMap { }.sorted { }...
  └─ Recommendation: Break into intermediate variables

  Sources/Views/Builder.swift:89
  └─ 8 chained calls
  └─ view.background().cornerRadius().shadow().padding()...
```

---

## Phase 2: Additional Patterns

---

## ⚠️ CRITICAL ANALYSIS: Pattern Implementation Challenges

### Pattern 7 (Variable Distinction) - Identified Issues

**Originally Estimated**: 19 hours
**Realistic Estimate**: 35-45 hours
**Status**: Requires research prototype before production implementation

#### Issue #1: Swift Scope Tracking Complexity
Swift has complex scoping rules that require handling:
- Pattern binding (`guard let x = foo() else { }` - x available AFTER guard)
- Conditional scoping (`if let y = bar() { }` - y only in block)
- Closure captures vs shadowing (captured vars vs local vars)
- Switch pattern scopes (case-specific bindings)
- Property shadowing in initializers (`init(name: String) { self.name = name }` - intentional!)

**Impact**: Scope tracking alone is 12-15 hours, not 3 hours as estimated.

#### Issue #2: Performance - Levenshtein O(n²)
For a file with 200 variables:
- Comparisons needed: 200 × 200 / 2 = 20,000
- Operations per comparison: O(name_length²) ≈ 64 for 8-char names
- Total: 1.28M operations per file
- For 50-file project: 64M operations

**Impact**: Could cause 2-3× slowdown, not "< 20% overhead" as claimed.

**Mitigation Required**:
- Compare only within same function (not file-wide)
- Length bucketing (skip if length diff > 2)
- Early exit on distance > 2

#### Issue #3: False Positive Explosion
**Plurals** (90% of similar name pairs):
```swift
let item = items.first     // Distance: 1 - INTENTIONAL
let result = results[0]    // Distance: 1 - INTENTIONAL
let data = datas.map {}    // Distance: 1 - INTENTIONAL
```

**Standard Swift Patterns**:
```swift
// Initializers - everyone does this
struct Config {
    let timeout: Int
    init(timeout: Int) { self.timeout = timeout }  // FALSE POSITIVE
}

// Closure parameters
items.map { item in item.name }  // "item" shadows outer? Common pattern!

// Protocol implementations
static func == (lhs: Foo, rhs: Foo) -> Bool  // lhs/rhs conventional
```

**Acceptable Single Letters**:
```swift
func transform<T>(_ value: T) -> T  // T is standard
let color = Color(r: 0.5, g: 0.3, b: 0.8, a: 1.0)  // r,g,b,a conventional
```

**Impact**: Estimated 60-70% false positive rate without sophisticated filtering.

#### Issue #4: Architecture Mismatch
Current analyzers are **stateless visitors**. Pattern 7 needs:
- Global state (all variables in file)
- Scope stack maintenance
- Post-processing (Levenshtein comparisons after walk)
- Complex filtering logic

This is a fundamentally different analyzer architecture.

#### Issue #5: Testing Complexity
Needs comprehensive tests for:
- Guard/if/switch scoping edge cases
- Closure capture vs shadowing
- Property/initializer patterns
- Plural false positive filters
- Generic type parameters
- Performance on large files

**Impact**: 8-10 hours minimum for proper test coverage.

---

### Recommendation: Do Pattern 2 First

**Pattern 2 (Novelty Detection)** is:
- ✅ Simple (4 hours vs 40 hours)
- ✅ Low risk (token matching only)
- ✅ Predictable (no false positive issues)
- ✅ Educational value
- ✅ Fits existing architecture

**Pattern 7** should be:
- Prototyped separately
- Tested on real codebases
- Refined based on user feedback
- Implemented only if false positives can be controlled

---

## Phase 2: Pattern Implementations

### 📋 Pattern 2: Novelty Detection (RECOMMENDED FIRST)

**What to Detect:**
- Variable shadowing (inner scope redefines outer variable)
- Similar variable names (Levenshtein distance < 3)
- Single-letter variables (excluding standard loop indices: i, j, k)

**Technical Approach:**

```swift
struct DistinctionMetrics: Codable {
    let shadowingCount: Int
    let similarNamePairs: Int
    let singleLetterCount: Int
    let locations: [DistinctionIssue]
}

struct DistinctionIssue: Codable {
    enum IssueType: String, Codable {
        case shadowing, similarNames, singleLetter
    }
    let type: IssueType
    let line: Int
    let variableName: String
    let details: String
}

class DistinctionAnalyzer: SyntaxVisitor {
    private var scopeStack: [[String: Int]] = [[:]]  // stack of [varName: declLine]
    private var issues: [DistinctionIssue] = []

    // Levenshtein distance for similarity detection
    private func levenshteinDistance(_ s1: String, _ s2: String) -> Int {
        // Standard Levenshtein implementation
        // ...
    }
}
```

**⚠️ COMPLEXITY WARNING**: This pattern requires:
- Sophisticated scope tracking (12-15 hours)
- Performance optimization for Levenshtein (avoid O(n²) explosion)
- Extensive false positive filtering (plurals, initializers, closures)
- Non-standard analyzer architecture (stateful, post-processing)
- Comprehensive testing (8-10 hours)

**Total Realistic Effort**: 35-45 hours

**Recommendation**:
1. Prototype in separate branch
2. Test on 10+ real-world codebases
3. Measure false positive rate
4. Iterate on filtering heuristics
5. Only merge if FP rate < 20%

**Output Format (TUI):**
```
VARIABLE NAMING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: 3 shadowing issues │ 8 similar name pairs │ 12 single-letter vars

⚠️  Naming Issues:
  Sources/Parser/Lexer.swift:234
  └─ Shadowing: 'token' redefined in inner scope

  Sources/Utils/String+Ext.swift:45
  └─ Similar names: 'data' and 'dата' (different characters)
```

---

### 📋 Pattern 2: Novelty Detection ⭐ IMPLEMENT FIRST

**What to Detect:**
- Custom operators
- Rarely-used Swift features (`rethrows`, `indirect`, `@dynamicMemberLookup`)
- Advanced attributes

**Why First:**
- ✅ Simple implementation (4 hours)
- ✅ Low risk (no false positives)
- ✅ Fits existing architecture
- ✅ Educational value

**Technical Approach:**

```swift
struct NoveltyMetrics: Codable {
    let customOperatorCount: Int
    let advancedFeatures: [String: Int]  // feature name -> count
    let locations: [NoveltyLocation]

    static var empty: NoveltyMetrics {
        NoveltyMetrics(
            customOperatorCount: 0,
            advancedFeatures: [:],
            locations: []
        )
    }
}

struct NoveltyLocation: Codable {
    let line: Int
    let column: Int
    let feature: String
    let context: String  // snippet of code
}

class NoveltyAnalyzer: SyntaxVisitor {
    private var customOperators: [NoveltyLocation] = []
    private var advancedFeatures: [String: [Int]] = [:]
    private let converter: SourceLocationConverter

    private let advancedAttributes: Set<String> = [
        "dynamicMemberLookup", "dynamicCallable",
        "propertyWrapper", "resultBuilder"
    ]

    init(viewMode: SyntaxTreeViewMode, converter: SourceLocationConverter) {
        self.converter = converter
        super.init(viewMode: viewMode)
    }

    override func visit(_ node: OperatorDeclSyntax) -> SyntaxVisitorContinueKind {
        let location = converter.location(for: node.position)
        let snippet = String(node.description.prefix(60))

        customOperators.append(NoveltyLocation(
            line: location.line,
            column: location.column,
            feature: "custom operator",
            context: snippet
        ))
        return .visitChildren
    }

    override func visit(_ node: AttributeSyntax) -> SyntaxVisitorContinueKind {
        let attrName = node.attributeName.trimmedDescription
        if advancedAttributes.contains(attrName) {
            let location = converter.location(for: node.position)
            advancedFeatures[attrName, default: []].append(location.line)
        }
        return .visitChildren
    }

    func calculateMetrics() -> NoveltyMetrics {
        // Sort locations by line
        let sortedLocations = customOperators.sorted { $0.line < $1.line }

        return NoveltyMetrics(
            customOperatorCount: customOperators.count,
            advancedFeatures: advancedFeatures.mapValues { $0.count },
            locations: Array(sortedLocations.prefix(10))  // Top 10
        )
    }
}
```

**Integration Points:**
- Add `NoveltyMetrics` to `HalsteadMetrics` (optional field)
- Call in `MetricsCalculator.calculateWithSets()` after other analyzers
- Add `formatNoveltyAnalysis()` function for TUI

**Output Format (TUI):**
```
CODE NOVELTY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Project: 2 custom operators │ 5 advanced features used

Advanced Features:
  • @resultBuilder: 3 occurrences
  • @propertyWrapper: 2 occurrences

⚠️  Custom Operators:
  Sources/Math/Operators.swift:12
  └─ infix operator ⊕ : AdditionPrecedence

💡 Tip: Document custom operators and advanced features for team awareness
```

**Implementation Estimate**: 4 hours total
- Data structures: 30 min
- Analyzer implementation: 1.5 hours
- TUI formatting: 1 hour
- Testing: 1 hour

---

### 📋 Pattern 7: Variable Distinction (DEFER - Complex)

**What to Detect:**

---

## Implementation Strategy

### Step 1: Data Structure Changes
```swift
// Extend HalsteadMetrics
struct HalsteadMetrics: Codable {
    // ... existing fields ...

    // Phase 1: Quick Wins
    var nesting: NestingMetrics?
    var conditionals: ConditionalMetrics?
    var liveness: LivenessMetrics?
    var grouping: GroupingMetrics?

    // Phase 2: Additional
    var distinction: DistinctionMetrics?
    var novelty: NoveltyMetrics?
}
```

### Step 2: Analyzer Integration
```swift
class MetricsCalculator {
    func calculateWithSets(for fileURL: URL) throws -> MetricsWithSets {
        let source = try String(contentsOf: fileURL, encoding: .utf8)
        let tree = Parser.parse(source: source)

        var metrics = HalsteadMetrics(path: fileURL.path)

        // Existing operator/operand counting...

        // NEW: Run readability analyzers
        let nestingAnalyzer = NestingAnalyzer(viewMode: .sourceAccurate)
        tree.walk(nestingAnalyzer)
        metrics.nesting = nestingAnalyzer.calculateMetrics()

        let conditionalAnalyzer = ConditionalAnalyzer(viewMode: .sourceAccurate)
        tree.walk(conditionalAnalyzer)
        metrics.conditionals = conditionalAnalyzer.calculateMetrics()

        // ... etc for other analyzers

        return MetricsWithSets(...)
    }
}
```

### Step 3: TUI Output Enhancement
```swift
func formatAsSummary(_ fileMetrics: [HalsteadMetrics], totals: HalsteadMetrics, verbose: Bool) -> String {
    var output = ""

    // Existing sections...
    output += formatSummaryHeader(...)
    output += formatRiskDistribution(...)
    output += formatArchitectureHotspots(...)

    // NEW: Readability pattern sections
    output += formatNestingAnalysis(fileMetrics)
    output += formatConditionalAnalysis(fileMetrics)
    output += formatLivenessAnalysis(fileMetrics)
    output += formatGroupingAnalysis(fileMetrics)

    // Existing sections...
    output += formatFilesNeedingAttention(...)
    output += formatProjectSummary(...)

    return output
}
```

### Step 4: JSON Output Schema
```swift
// Backward compatible - new fields are optional
// Existing tools will ignore new fields
{
  "files": [
    {
      "path": "...",
      "n1": 25,
      // ... existing metrics ...
      "nesting": {
        "maxDepth": 8,
        "avgDepth": 3.2,
        "deeplyNestedCount": 2,
        "locations": [...]
      },
      "conditionals": { ... },
      "liveness": { ... },
      "grouping": { ... }
    }
  ]
}
```

---

## Testing Strategy

### Unit Tests (per pattern)
```swift
// Tests/SwiftHALTests/NestingTests.swift
final class NestingTests: XCTestCase {
    func testSimpleNesting() throws {
        let source = """
        func foo() {
            if true {
                print("depth 2")
            }
        }
        """
        let analyzer = NestingAnalyzer()
        // ... assertions
    }

    func testDeepNesting() throws {
        // Test 8-level nesting
    }
}
```

### Acceptance Tests
```swift
// Add to AcceptanceTests.swift
func testReadabilityPatterns() throws {
    // Run on SwiftHAL itself
    let result = try MetricsCalculator().calculate(for: swiftHALSource)

    XCTAssertNotNil(result.nesting)
    XCTAssertLessThan(result.nesting!.maxDepth, 8)  // Self-check
}
```

---

## CLI Interface (Backward Compatible)

### New Flags
```bash
# Show only readability patterns (skip Halstead metrics)
hal --path Sources --patterns-only

# Include specific patterns in summary
hal --path Sources --patterns nesting,conditionals

# Patterns in JSON output (default: included if available)
hal --path Sources --format json --exclude-patterns
```

### Threshold Support
```bash
# Fail build on pattern violations
hal --path Sources \
    --threshold "volume>800,nesting.maxDepth>6,conditionals.avgOperators>5"
```

---

## Migration Path

1. ✅ **v2.1**: Add all Phase 1 patterns (Nesting, Conditionals, Liveness, Grouping)
   - ✅ Proved concept
   - ✅ All 4 patterns working
   - ✅ Comprehensive TUI format with visual sections

2. **v2.2** (Next Release): Add Pattern 2 (Novelty Detection)
   - Custom operator detection
   - Advanced Swift feature tracking
   - **Estimated**: 4 hours implementation + testing
   - Low risk, high confidence

3. **v2.3** (Future): Research Pattern 7 (Variable Distinction)
   - Prototype in separate branch
   - Test on real codebases
   - Measure false positive rates
   - Refine filtering heuristics
   - **Estimated**: 35-45 hours (research + implementation)
   - High risk, requires validation

4. **v2.4+** (Future): Advanced features
   - Custom threshold configuration
   - Trend tracking across commits
   - Auto-fix suggestions
   - Pattern 7 if prototype successful

---

## Technical Considerations

### Performance
- Run all analyzers in single AST walk (avoid reparsing)
- Use `SyntaxVisitor` base class for consistent traversal
- Cache results per file

### Memory
- Limit stored locations (e.g., top 10 worst per pattern)
- Use lazy evaluation for verbose output

### SwiftSyntax Version
- Current: 602.0.0
- Required features: `SyntaxVisitor`, position tracking (✓ available)

### Backward Compatibility
- All new metrics are optional in `HalsteadMetrics`
- JSON output includes new fields only if calculated
- CLI flags default to current behavior
- Tests for old output format remain valid

---

## Documentation Requirements

### README Updates
- Add "Readability Patterns" section
- Update "Understanding Risk Score" with new categories
- Add interpretation guide for each pattern

### New Doc: PATTERNS.md
```markdown
# SwiftHAL Readability Patterns

## Overview
Explanation of each pattern, what it measures, why it matters

## Interpreting Results
Guidelines for each metric category

## Refactoring Strategies
Specific recommendations for fixing issues

## Case Studies
Real-world examples from open source Swift projects
```

---

## Success Metrics

### Quantitative
- Pattern detection accuracy: >95% (validated against manual review)
- Performance impact: <10% slowdown vs current version
- False positive rate: <5% per pattern

### Qualitative
- Developer feedback: patterns are actionable
- Refactoring success: metrics improve after following guidance
- Adoption: patterns used in CI/CD pipelines

---

## Open Questions

1. **Pattern Weighting**: Should we create a unified "readability score" combining all patterns, or keep them separate?

2. **Severity Levels**: Should we distinguish between "warning" and "error" levels per pattern?

3. **Auto-fix Suggestions**: Should SwiftHAL suggest specific refactorings (e.g., "extract this to a helper function")?

4. **Project Trends**: Should we support comparing metrics across commits/branches (requires storage)?

5. **Custom Thresholds**: Should users be able to configure thresholds per-pattern in a config file?

---

## Resources

- [Visual Readability Patterns](https://seeinglogic.com/posts/visual-readability-patterns/)
- [SwiftSyntax Documentation](https://swiftpackageindex.com/swiftlang/swift-syntax)
- [SyntaxVisitor Guide](https://swiftpackageindex.com/swiftlang/swift-syntax/main/documentation/swiftsyntax/syntaxvisitor)

---

**Status**: Phase 1 Complete ✅
**Completed**: All 4 Phase 1 patterns implemented and tested
**Next Action**: Implement Pattern 2 (Novelty Detection) for v2.2
**Deferred**: Pattern 7 (Variable Distinction) - requires research prototype
**Current Version**: v2.1 with Phase 1 patterns

---

## Implementation Timeline (Revised)

### v2.1 (CURRENT) ✅
- All Phase 1 patterns complete
- Nesting, Conditionals, Liveness, Grouping working

### v2.2 (NEXT - 4 hours)
- Pattern 2: Novelty Detection
- Custom operators + advanced features
- Low risk, quick win

### v2.3 (RESEARCH - 35-45 hours)
- Pattern 7: Prototype & validate
- Scope tracking implementation
- False positive filtering
- Performance optimization
- Only merge if successful

### v2.4+ (TBD)
- Pattern 7 production (if prototype succeeds)
- Advanced configuration features
- Trend tracking
