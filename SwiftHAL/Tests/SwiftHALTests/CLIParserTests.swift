import XCTest
@testable import SwiftHAL

final class CLIParserTests: XCTestCase {

    private func parse(_ args: [String]) throws -> SwiftHAL {
        try SwiftHAL.parse(args)
    }

    func test_default_path_is_dot() throws {
        let command = try parse([])
        XCTAssertEqual(command.path, ".")
    }

    func test_path_flag_overrides_positional() throws {
        let command = try parse(["Sources", "--path", "Tests"])
        XCTAssertEqual(command.path, "Tests")
    }

    func test_path_flag_parses_correctly() throws {
        let command = try parse(["--path", "Sources"])
        XCTAssertEqual(command.pathOption, "Sources")
    }

    func test_format_flag_parses_json() throws {
        let command = try parse(["--format", "json"])
        XCTAssertEqual(command.format, .json)
    }

    func test_format_flag_parses_table() throws {
        let command = try parse(["--format", "table"])
        XCTAssertEqual(command.format, .table)
    }

    func test_format_default_is_summary() throws {
        let command = try parse([])
        XCTAssertEqual(command.format, .summary)
    }

    func test_threshold_flag_parses_correctly() throws {
        let command = try parse(["--threshold", "volume>800"])
        XCTAssertEqual(command.threshold, "volume>800")
    }

    func test_threshold_flag_splits_comma_separated_list() throws {
        let command = try parse(["--threshold", "volume>800,difficulty>=30"])
        XCTAssertEqual(command.thresholdList, ["volume>800", "difficulty>=30"])
        XCTAssertNoThrow(try command.thresholdList!.map { try parseThreshold($0) })
    }

    func test_output_flag_parses_correctly() throws {
        let command = try parse(["--output", "halstead.json"])
        XCTAssertEqual(command.output, "halstead.json")
    }

    func test_include_tests_flag_parses_correctly() throws {
        let command = try parse(["--include-tests"])
        XCTAssertTrue(command.includeTests)
    }

    func test_help_flag_exits() {
        XCTAssertThrowsError(try parse(["--help"]))
    }

    func test_invalid_format_throws_error() {
        XCTAssertThrowsError(try parse(["--format", "invalid"]))
    }

    func test_removed_include_option_throws_error() {
        XCTAssertThrowsError(try parse(["--include", "**/*.swift"]))
    }

    func test_explainFlag_setsExplain() throws {
        let command = try parse(["--explain"])
        XCTAssertTrue(command.explain)
    }

    func test_verboseFlag_setsVerbose() throws {
        let command = try parse(["--verbose"])
        XCTAssertTrue(command.verbose)
    }

    func test_vFlag_setsVerbose() throws {
        let command = try parse(["-v"])
        XCTAssertTrue(command.verbose)
    }

    func test_summaryFormat_parsesCorrectly() throws {
        let command = try parse(["--format", "summary"])
        XCTAssertEqual(command.format, .summary)
    }

    func test_positional_path_argument_parses_correctly() throws {
        let command = try parse(["../../contactripple"])
        XCTAssertEqual(command.pathArgument, "../../contactripple")
    }

    func test_positional_path_with_flags_parses_correctly() throws {
        let command = try parse(["Sources", "--format", "json"])
        XCTAssertEqual(command.pathArgument, "Sources")
        XCTAssertEqual(command.format, .json)
    }
}
