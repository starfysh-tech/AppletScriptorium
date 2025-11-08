# Swift CLI for Halstead Metrics (SwiftHAL) - Project Requirements

## Goal

Create a SwiftPM executable named `hal` that computes Halstead metrics for Swift source code, outputs JSON suitable for CI, and can recurse a project tree. The tool must use `SwiftSyntax` for parsing and tokenization.

## Scope

*   **Input:** A path to a file or directory.
*   **Output:** Per-file metrics plus repository totals in JSON format. An optional table output format is also required.
*   **Target:** macOS 13+
*   **Parser:** SwiftSyntax + SwiftParser.

## References for Counting Rules

*   **Halstead formulas:** Vocabulary, length, estimated length, volume, difficulty, effort, time, and bugs. Use `B = V / 3000`. (Wikipedia: [Halstead complexity measures](https://en.wikipedia.org/wiki/Halstead_complexity_measures))
*   **Swift token kinds and iteration:** `TokenKind`, `TokenSequence`, source-accurate traversal. (The Swift Package Index: [TokenKind Documentation](https://swiftpackageindex.com/swiftlang/swift-syntax/601.0.0-prerelease-2024-10-22/documentation/swiftsyntax/tokenkind))
*   **Alternative tokenizer considered for validation:** SourceKitten CLI `--syntax` output. This should *not* be a build dependency. A smoke-test script comparing counts on a few files can be provided. (JP Simard: [sourcekitten Reference](https://www.jpsim.com/SourceKitten/))

## Deliverables

1.  **SwiftPM Repository:**
    *   `Package.swift` with dependencies on `SwiftSyntax` and `SwiftParser`.
    *   Executable target `hal`.
    *   MIT license and `README.md`.
2.  **CLI Binary:** The compiled `hal` executable.
3.  **Tests:**
    *   Unit tests for counting logic and Halstead formulas.
    *   Golden tests with sample Swift files and expected outputs.
4.  **Example Outputs:** Sample JSON and table outputs.
5.  **CI Workflow:** A GitHub Actions workflow to build, run tests, and execute the tool on its own `Sources/` directory to produce an artifact.

## CLI Specification

```
hal --path <dir-or-file> [--include-tests] [--by file|function] [--format json|table]
    [--threshold 'volume>800,difficulty>20'] [--include '**/*.swift'] [--exclude 'Tests/**']
    [--output <path>]
```

*   **Default granularity:** By file.
*   `--by function` is an optional stretch goal if function-level counts can be computed via SwiftSyntax function declarations.
*   **Exit Codes:** Exit 2 if any threshold fails. Exit 1 on other errors.

## JSON Schema

```json
{
  "files": [
    {
      "path": "Sources/MyLib/Foo.swift",
      "n1": 0, "n2": 0, "N1": 0, "N2": 0,
      "vocabulary": 0, "length": 0,
      "estimatedLength": 0.0,
      "volume": 0.0, "difficulty": 0.0, "effort": 0.0,
      "timeSeconds": 0.0, "bugs": 0.0
    }
  ],
  "totals": {
    "path": "TOTALS",
    "n1": 0, "n2": 0, "N1": 0, "N2": 0,
    "vocabulary": 0, "length": 0,
    "estimatedLength": 0.0,
    "volume": 0.0, "difficulty": 0.0, "effort": 0.0,
    "timeSeconds": 0.0, "bugs": 0.0
  }
}
```

## Counting Model

### Operators

Count as operators:

*   Operator tokens: `binaryOperator`, `prefixOperator`, `postfixOperator`.
*   Punctuation that performs operations: assignment `=`, arithmetic `+ - * / %`, bitwise `& | ^`, shift `<< >>`, comparison `< > <= >= == !=`, boolean `! ?`, range `... ..<`, arrow `->`, colon `:`, semicolon `;`, comma `,`, dot `.`.
*   Control and declaration keywords treated as operators for Halstead counting: `if else for while repeat switch case default guard`, `func class struct enum protocol`, `import let var in return break continue defer`, `throw throws rethrows try`, `do catch`, `where as is`.

### Operands

Count as operands:

*   Identifiers, literals: integer, floating, string, regex, `true`, `false`, `nil`.

### Totals and Distincts

*   `N1` and `N2` are total occurrences across tokens classified above.
*   `n1` and `n2` are counts of distinct texts for operators and operands respectively.
*   Treat operator text exactly as lexed, including custom operator spellings.
*   Ignore comments and whitespace.

### Derived Metrics

*   `n = n1 + n2`
*   `N = N1 + N2`
*   `N_hat = n1 * log2(n1) + n2 * log2(n2)` (Handle `n1=0` or `n2=0` by returning 0 for that term)
*   `V = N * log2(n)` (Handle `n=0` by returning 0)
*   `D = (n1 / 2) * (N2 / n2)` (Handle `n2=0` by returning 0)
*   `E = D * V`
*   `T = E / 18`
*   `B = V / 3000`

### Edge Cases

*   If `n == 0` or `n2 == 0`, avoid divide by zero. Return zeros for dependent metrics.
*   Skip generated files under `DerivedData` or hidden directories by default.

## Architecture

*   Parse each file with `SwiftParser.parse` and iterate tokens with `tokens(viewMode: .sourceAccurate)`.
*   Classify tokens as operator or operand using `TokenKind`.
*   Maintain two `Set<String>` for operator and operand distincts, and two integer totals.
*   Aggregate per-file results, then compute totals.

## `Package.swift` Requirements

*   Add `swift-syntax` as a dependency. Use the current documented product names `SwiftSyntax` and `SwiftParser`. The version used is `602.0.0`.

## CLI Details

*   **Flags:** Implement with a robust argument parser (e.g., `swift-argument-parser` if appropriate, or a custom minimal parser).
*   **Glob Patterns:** `--include` or `--exclude` patterns should resolve against the walked file list.
*   `--by function` stretch: Visit function declarations and recompute counts inside each function subtree.

## Output Formats

*   **JSON:** Pretty printed by default, with `--format json` controlling this.
*   **Table:** Aligned columns, similar to `cloc` output.

## Thresholds and Exit Codes

*   Parse `--threshold` pairs (e.g., `'volume>800,difficulty>20'`). Supported comparators: `> >= < <= ==`.
*   If any threshold is violated for any file or totals, print a one-line summary and exit with code 2.
*   Exit with code 1 on other errors.

## Testing Strategy

*   **Unit Tests:**
    *   For token classification (e.g., custom operator `infix operator ⊕`, literals, identifiers).
    *   For Halstead formula calculations with fixed token counts.
*   **Golden Tests:**
    *   Small sample Swift files covering control flow, declarations, operators, and literals.
    *   Compare CLI output (JSON/table) against stored "golden" files.
*   **Cross-check script:** An optional script running `sourcekitten syntax` to sanity-check operator vs operand distributions on a sample file (not a build dependency).

## Performance

*   Use a single pass over `TokenSequence` per file. No AST traversal required for file-level metrics.
*   Parallelize by file using a simple operation queue.

## Non-Goals

*   No language server.
*   No editor plugin.
*   No dependency on SourceKitten or Tree-sitter for core logic.

## `README.md` Checklist

*   Explain Halstead briefly with formulas and references.
*   Show install via `swift build -c release`.
*   Usage examples.
*   JSON schema snippet.
*   Notes on counting rules tied to `TokenKind` docs.

## Acceptance Criteria

*   Build succeeds on macOS 13+ with the latest Swift toolchain.
*   Running on the repository prints valid JSON with at least one file entry and a totals block.
*   `--format table` renders a table with columns: path, n, N, volume, difficulty, effort, time, bugs.
*   Thresholds work and affect exit code.
*   Unit tests pass and include at least 10 focused cases.
*   `README.md` includes references with links to SwiftSyntax `TokenKind` and a Halstead reference.

## Nice to Have (Stretch Goals)

*   `--by function` output with a nested JSON array.
*   `--cache` keyed by file path and mtime.
*   `--exclude-generated` to skip files containing an autogenerated header.

---

## Current Project State (as of Handover)

The project is initialized and partially implemented.

### Project Structure:

```
/Users/randallnoval/Code/AppletScriptorium/SwiftHAL/
├── .build/
├── .git/
├── Package.swift
├── README.md
├── LICENSE
├── Sources/
│   └── SwiftHAL/
│       └── SwiftHAL.swift
└── Tests/
    └── SwiftHALTests/
        ├── Fixtures/  (empty, created for golden tests)
        └── SwiftHALTests.swift
```

### `Package.swift` Content:

```swift
// swift-tools-version: 6.2
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "SwiftHAL",
    platforms: [
        .macOS(.v13)
    ],
    dependencies: [
        .package(url: "https://github.com/swiftlang/swift-syntax.git", from: "602.0.0"),
    ],
    targets: [
        // Targets are the basic building blocks of a package, defining a module or a test suite.
        // Targets can depend on other targets in this package and products from dependencies.
        .executableTarget(
            name: "SwiftHAL",
            dependencies: [
                .product(name: "SwiftSyntax", package: "swift-syntax"),
                .product(name: "SwiftParser", package: "swift-syntax"),
            ]
        ),
        .testTarget(
            name: "SwiftHALTests",
            dependencies: ["SwiftHAL"]),
    ]
)
```

### `Sources/SwiftHAL/SwiftHAL.swift` Content:

```swift
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
    var bugs: Double { volume / 3000.0 }
    
    init(path: String) {
        self.path = path
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
        // The crucial fix: use token.tokenKind instead of token.kind
        switch token.tokenKind {
        
        // MARK: Operators
        case .binaryOperator(_), .prefixOperator(_), .postfixOperator(_):
            return .operator
            
        // Punctuation that are operators
        case .equal, .plus, .minus, .star, .slash, .percent,
             .ampersand, .pipe, .caret, .leftShift, .rightShift,
             .leftAngle, .rightAngle, .ellipsis, .halfOpenRange,
             .colon, .semicolon, .comma, .dot,
             .arrow, .exclamationMark, .questionMark:
            return .operator

        // Keywords that are operators
        case .`if`, .`else`, .`for`, .`while`, .`repeat`, .`switch`, .`case`, .`default`, .`guard`,
             .`func`, .`class`, .`struct`, .`enum`, .`protocol`, .`import`, .`let`, .`var`, .`in`,
             .`return`, .`break`, .`continue`, .`defer`, .`throw`, .`throws`, .`rethrows`,
             .`try`, .`do`, .`catch`, .`where`, .`as`, .`is`:
            return .operator
            
        // MARK: Operands
        case .identifier(_):
            return .operand
        case .integerLiteral(_), .floatLiteral(_), .stringLiteral(_), .regexLiteral(_):
            return .operand
        // Keywords that are operands
        case .`true`, .`false`, .`nil`:
            return .operand
            
        // MARK: Ignored
        default:
            return .ignored
        }
    }
}

// MARK: - Metrics Calculation

class MetricsCalculator {
    func calculate(for fileURL: URL) throws -> HalsteadMetrics {
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
        
        return metrics
    }
}


@main
struct SwiftHAL {

    static func main() {
        // Basic argument parsing (will be expanded later)
        let path = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "."

        let fileManager = FileManager.default
        let rootURL = URL(fileURLWithPath: path)

        let swiftFiles = findSwiftFiles(at: rootURL, fileManager: fileManager)
        let calculator = MetricsCalculator()

        print("Analyzing \(swiftFiles.count) Swift files...")

        for fileURL in swiftFiles {
            do {
                let metrics = try calculator.calculate(for: fileURL)
                print("File: \(metrics.path)")
                print("  Vocabulary: \(metrics.vocabulary), Length: \(metrics.length), Volume: \(String(format: "%.2f", metrics.volume))")
                print("  Difficulty: \(String(format: "%.2f", metrics.difficulty)), Effort: \(String(format: "%.2f", metrics.effort)), Bugs: \(String(format: "%.2f", metrics.bugs))")
            } catch {
                print("Error calculating metrics for \(fileURL.path): \(error)")
            }
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
```

### Work Completed:

*   **Project Initialization:** The SwiftPM project `SwiftHAL` has been set up.
*   **Dependencies:** `swift-syntax` (version `602.0.0`) is correctly configured in `Package.swift`.
*   **Basic File Structure:** `LICENSE`, `README.md`, `Sources/SwiftHAL/SwiftHAL.swift`, `Tests/SwiftHALTests/Fixtures/` are in place.
*   **File Discovery:** A recursive function `findSwiftFiles` is implemented to locate `.swift` files.
*   **Metrics Data Structure:** `HalsteadMetrics` struct is defined with properties for raw counts and calculated metrics.
*   **Metrics Calculation Skeleton:** `MetricsCalculator` class is set up to parse files and iterate tokens.

### Outstanding Issues / Blockers:

1.  **Critical: `SwiftSyntax` `TokenClassifier` Compilation Errors:**
    *   The `TokenClassifier` struct, responsible for categorizing `TokenSyntax` objects into operators, operands, or ignored, is currently **failing to compile**.
    *   The persistent error is `error: pattern of type 'TokenKind' cannot match 'SyntaxKind'`. This occurs when attempting to `switch` on `token.tokenKind` (which is of type `TokenKind`) using `TokenKind` enum cases.
    *   This indicates a fundamental misunderstanding of the `TokenKind` enum's exact structure for `SwiftSyntax` version `602.0.0` or a type resolution issue within the compiler's context.
    *   **The immediate priority for the new agent is to correctly implement the `TokenClassifier` to compile successfully.** This will likely require a precise understanding of the `TokenKind` enum's cases, including how to handle associated values (e.g., `identifier(String)`) and direct keyword cases (e.g., `.if`, `.true`). Inspecting the official `swift-syntax` GitHub repository for tag `602.0.0` and locating the `TokenKind.swift` source file is highly recommended.

2.  **Environmental Instability (macOS Seatbelt Sandbox):**
    *   The execution environment intermittently applies a strict sandbox profile (macOS Seatbelt), leading to `sandbox-exec: sandbox_apply: Operation not permitted` errors when running `swift build` or `swift run`.
    *   This has caused frequent interruptions and made iterative development and testing extremely difficult. The user has been able to temporarily resolve this, but it has recurred multiple times.
    *   The new agent should be aware of this potential blocker and be prepared to guide the user on resolving it if it reappears, as it prevents the tool from running.

### Next Steps for New AI Agent:

1.  **Resolve `TokenClassifier` Compilation Errors (Highest Priority):**
    *   **Action:** Accurately determine the `TokenKind` enum structure for `swift-syntax` version `602.0.0` by inspecting its source code.
    *   **Implementation:** Rewrite the `TokenClassifier.classify` function in `Sources/SwiftHAL/SwiftHAL.swift` to correctly pattern match all relevant `TokenKind` cases as defined in the project brief (operators, operands, ignored).
2.  **Implement Robust CLI Argument Parsing:**
    *   Replace the basic `CommandLine.arguments` parsing with a more robust solution (e.g., `swift-argument-parser` or a custom parser) to handle all specified CLI flags (`--path`, `--include-tests`, `--by`, `--format`, `--threshold`, `--include`, `--exclude`, `--output`).
3.  **Complete Metrics Calculation and Aggregation:**
    *   Ensure `MetricsCalculator` correctly populates `HalsteadMetrics` for each file.
    *   Implement logic to aggregate per-file metrics into a `totals` block.
4.  **Implement Output Formats:**
    *   Develop JSON output conforming to the specified schema.
    *   Develop table output with aligned columns.
5.  **Implement Threshold Checking and Exit Codes:**
    *   Parse and evaluate `--threshold` arguments.
    *   Set appropriate process exit codes (0 for success, 1 for general errors, 2 for threshold violations).
6.  **Develop Comprehensive Tests:**
    *   Create unit tests for `TokenClassifier` and Halstead formula calculations.
    *   Develop golden tests using sample Swift files.
7.  **Set Up CI Workflow:**
    *   Create a GitHub Actions workflow for building, testing, and running the tool.
8.  **Finalize Documentation:**
    *   Complete the `README.md` as per the project brief's checklist.

