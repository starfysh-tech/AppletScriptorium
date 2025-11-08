import XCTest
@testable import SwiftHAL

final class CLIParserTests: XCTestCase {

    func test_default_path_is_dot() throws {
        let options = try parse_arguments(["hal"])
        XCTAssertEqual(options.path, ".")
    }

    func test_path_flag_parses_correctly() throws {
        let options = try parse_arguments(["hal", "--path", "Sources"])
        XCTAssertEqual(options.path, "Sources")
    }

    func test_format_flag_parses_json() throws {
        let options = try parse_arguments(["hal", "--format", "json"])
        XCTAssertEqual(options.format, .json)
    }

    func test_format_flag_parses_table() throws {
        let options = try parse_arguments(["hal", "--format", "table"])
        XCTAssertEqual(options.format, .table)
    }

    func test_format_default_is_summary() throws {
        let options = try parse_arguments(["hal"])
        XCTAssertEqual(options.format, .summary)
    }

    func test_threshold_flag_parses_correctly() throws {
        let options = try parse_arguments(["hal", "--threshold", "volume>800"])
        XCTAssertEqual(options.thresholds?.count, 1)
    }

    func test_multiple_thresholds_parse_correctly() throws {
        let options = try parse_arguments(["hal", "--threshold", "volume>800,difficulty>20"])
        XCTAssertEqual(options.thresholds?.count, 2)
    }

    func test_output_flag_parses_correctly() throws {
        let options = try parse_arguments(["hal", "--output", "halstead.json"])
        XCTAssertEqual(options.output_path, "halstead.json")
    }

    func test_include_tests_flag_parses_correctly() throws {
        let options = try parse_arguments(["hal", "--include-tests"])
        XCTAssertTrue(options.include_tests)
    }

    func test_help_flag_sets_help_true() throws {
        let options = try parse_arguments(["hal", "--help"])
        XCTAssertTrue(options.show_help)
    }

    func test_invalid_format_throws_error() {
        XCTAssertThrowsError(try parse_arguments(["hal", "--format", "invalid"]))
    }

    func test_include_flag_parses_correctly() throws {
        let options = try parse_arguments(["hal", "--include", "**/*.swift"])
        XCTAssertEqual(options.include, "**/*.swift")
    }

    func test_exclude_flag_parses_correctly() throws {
        let options = try parse_arguments(["hal", "--exclude", "Tests/**"])
        XCTAssertEqual(options.exclude, "Tests/**")
    }

    func test_explainFlag_setsShowExplanation() throws {
        let options = try parse_arguments(["hal", "--explain"])
        XCTAssertTrue(options.show_explanation)
    }

    func test_verboseFlag_setsVerbose() throws {
        let options = try parse_arguments(["hal", "--verbose"])
        XCTAssertTrue(options.verbose)
    }

    func test_vFlag_setsVerbose() throws {
        let options = try parse_arguments(["hal", "-v"])
        XCTAssertTrue(options.verbose)
    }

    func test_summaryFormat_parsesCorrectly() throws {
        let options = try parse_arguments(["hal", "--format", "summary"])
        XCTAssertEqual(options.format, .summary)
    }

    func test_positional_path_argument_parses_correctly() throws {
        let options = try parse_arguments(["hal", "../../contactripple"])
        XCTAssertEqual(options.path, "../../contactripple")
    }

    func test_positional_path_with_flags_parses_correctly() throws {
        let options = try parse_arguments(["hal", "Sources", "--format", "json"])
        XCTAssertEqual(options.path, "Sources")
        XCTAssertEqual(options.format, .json)
    }

    func test_path_flag_overrides_positional() throws {
        let options = try parse_arguments(["hal", "Sources", "--path", "Tests"])
        XCTAssertEqual(options.path, "Tests")
    }
}
