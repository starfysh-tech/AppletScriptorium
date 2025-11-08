# SwiftHAL

A Swift CLI tool for calculating Halstead complexity metrics on Swift source code using SwiftSyntax.

## What are Halstead Metrics?

Halstead complexity measures provide quantitative metrics about your code's complexity based on the count of operators and operands:

- **n1**: Number of distinct operators
- **n2**: Number of distinct operands
- **N1**: Total number of operators
- **N2**: Total number of operands
- **Vocabulary (n)**: n1 + n2
- **Length (N)**: N1 + N2
- **Volume (V)**: N × log₂(n) - measures the size of the implementation
- **Difficulty (D)**: (n1/2) × (N2/n2) - measures how difficult the code is to write or understand
- **Effort (E)**: D × V - the mental effort required to develop or understand the code
- **Time (T)**: E / 18 seconds - estimated time to program in seconds
- **Risk Score**: V / 3000 - statistical defect density estimate (NOT actual bugs)

[Learn more about Halstead complexity measures on Wikipedia](https://en.wikipedia.org/wiki/Halstead_complexity_measures)

## Understanding Risk Score

The "Risk Score" is a **statistical estimate** of defect density based on code volume and complexity. It is NOT a count of actual bugs.

**Formula:** Risk Score = Volume / 3000

**Interpretation:**
- < 0.5: Very low complexity
- 0.5-1.0: Low complexity
- 1.0-2.0: Moderate (typical business logic)
- 2.0-5.0: High (review recommended)
- > 5.0: Very high (refactoring candidate)

**Use it to:**
- Prioritize code reviews
- Allocate testing effort
- Identify refactoring opportunities
- Track complexity trends

**Don't use it to:**
- Count actual defects
- Report "bug counts" to stakeholders

## Installation

### Build from Source

```bash
git clone <repository-url>
cd SwiftHAL
swift build -c release
cp .build/release/SwiftHAL /usr/local/bin/hal
```

## Usage

### Basic Usage

```bash
# Smart summary (default - shows top/bottom 5 files)
hal --path ./Sources

# See all files
hal --path ./Sources --verbose

# Understand metrics
hal --explain

# Analyze current directory
hal

# Analyze single file
hal --path Sources/MyFile.swift
```

### Output Formats

**Table format (default):**
```bash
hal --path Sources --format table
```

**JSON format:**
```bash
hal --path Sources --format json > halstead.json
```

### Threshold Checking

Fail the build if metrics exceed thresholds:

```bash
# Single threshold
hal --path Sources --threshold "volume>800"

# Multiple thresholds
hal --path Sources --threshold "volume>800,difficulty>25"
```

Supported comparators: `>`, `>=`, `<`, `<=`, `==`

Supported metrics: `volume`, `difficulty`, `effort`, `riskScore`, `time`, `vocabulary`, `length`, `n1`, `n2`

### Advanced Options

```bash
# Write output to file
hal --path Sources --format json --output metrics.json

# Include test directories
hal --path . --include-tests

# Show all files (default shows top/bottom only)
hal --path Sources --verbose

# Show metric explanations
hal --explain

# Include/exclude patterns (future)
hal --path . --include "**/*.swift" --exclude "Tests/**"
```

### Exit Codes

- `0`: Success
- `1`: Error (file not found, parse error, etc.)
- `2`: Threshold violations

## JSON Output Schema

```json
{
  "files": [
    {
      "path": "Sources/MyLib/Foo.swift",
      "n1": 25,
      "n2": 30,
      "N1": 100,
      "N2": 120,
      "vocabulary": 55,
      "length": 220,
      "estimatedLength": 325.4,
      "volume": 1285.3,
      "difficulty": 25.0,
      "effort": 32132.5,
      "timeSeconds": 1785.1,
      "riskScore": 0.43
    }
  ],
  "totals": {
    "path": "TOTALS",
    "n1": 25,
    "n2": 30,
    ...
  }
}
```

## How Counting Works

### Operators

Counted as operators:
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Assignment: `=`
- Comparison: `<`, `>`, `<=`, `>=`, `==`, `!=`
- Logical: `!`, `&&`, `||`
- Control flow keywords: `if`, `else`, `for`, `while`, `switch`, `case`, `guard`, etc.
- Declaration keywords: `func`, `class`, `struct`, `enum`, `protocol`, `let`, `var`
- Other keywords: `import`, `return`, `break`, `continue`, `throw`, `try`, `catch`, etc.
- Punctuation: `:`, `;`, `,`, `.`, `->`, etc.
- Custom operators: `infix operator ⊕` counts as an operator

### Operands

Counted as operands:
- Identifiers: variable and function names
- Literals: integers, floats, strings, booleans (`true`, `false`)
- `nil`

### What's Ignored

- Comments
- Whitespace
- Structural tokens (braces, parentheses, brackets)

## Implementation Details

- **Parser**: SwiftSyntax 602.0.0 ([SwiftSyntax on Swift Package Index](https://swiftpackageindex.com/swiftlang/swift-syntax))
- **Tokenization**: Uses `tokens(viewMode: .sourceAccurate)` for exact token representation
- **Classification**: See `TokenKind` documentation for token types: [TokenKind docs](https://swiftpackageindex.com/swiftlang/swift-syntax/601.0.0-prerelease-2024-10-22/documentation/swiftsyntax/tokenkind)

## Development

### Running Tests

```bash
swift test
```

### Running on Self

```bash
swift run SwiftHAL --path Sources
```

Expected metrics (approximate):
- Vocabulary: ~200
- Volume: ~6300
- Difficulty: ~45

## CI Integration

Example GitHub Actions workflow:

```yaml
- name: Check Halstead Metrics
  run: |
    swift run SwiftHAL --path Sources \
      --threshold "volume>10000,difficulty>50,riskScore>5" \
      --format json --output halstead.json
```

## Breaking Changes

**v2.0.0:**
- JSON field renamed: `bugs` → `riskScore`
- Default output changed to smart summary (use `--verbose` for all files)

## License

MIT License (see LICENSE file)

## References

- [Halstead complexity measures (Wikipedia)](https://en.wikipedia.org/wiki/Halstead_complexity_measures)
- [SwiftSyntax](https://github.com/swiftlang/swift-syntax)
- [SwiftSyntax TokenKind](https://swiftpackageindex.com/swiftlang/swift-syntax/601.0.0-prerelease-2024-10-22/documentation/swiftsyntax/tokenkind)
