import XCTest
@testable import SwiftHAL

final class CLIParserTests: XCTestCase {

    func test_default_path_is_dot() throws {
        let options = try parseArguments(["hal"])
        XCTAssertEqual(options.path, ".")
    }

    func test_path_flag_parses_correctly() throws {
        let options = try parseArguments(["hal", "--path", "Sources"])
        XCTAssertEqual(options.path, "Sources")
    }

    func test_format_flag_parses_json() throws {
        let options = try parseArguments(["hal", "--format", "json"])
        XCTAssertEqual(options.format, .json)
    }

    func test_format_flag_parses_table() throws {
        let options = try parseArguments(["hal", "--format", "table"])
        XCTAssertEqual(options.format, .table)
    }

    func test_format_default_is_summary() throws {
        let options = try parseArguments(["hal"])
        XCTAssertEqual(options.format, .summary)
    }

    func test_threshold_flag_parses_correctly() throws {
        let options = try parseArguments(["hal", "--threshold", "volume>800"])
        XCTAssertEqual(options.thresholds?.count, 1)
    }

    func test_multiple_thresholds_parse_correctly() throws {
        let options = try parseArguments(["hal", "--threshold", "volume>800,difficulty>20"])
        XCTAssertEqual(options.thresholds?.count, 2)
    }

    func test_output_flag_parses_correctly() throws {
        let options = try parseArguments(["hal", "--output", "halstead.json"])
        XCTAssertEqual(options.output_path, "halstead.json")
    }

    func test_include_tests_flag_parses_correctly() throws {
        let options = try parseArguments(["hal", "--include-tests"])
        XCTAssertTrue(options.include_tests)
    }

    func test_help_flag_sets_help_true() throws {
        let options = try parseArguments(["hal", "--help"])
        XCTAssertTrue(options.show_help)
    }

    func test_invalid_format_throws_error() {
        XCTAssertThrowsError(try parseArguments(["hal", "--format", "invalid"]))
    }

    func test_include_flag_parses_correctly() throws {
        let options = try parseArguments(["hal", "--include", "**/*.swift"])
        XCTAssertEqual(options.include, "**/*.swift")
    }

    func test_exclude_flag_parses_correctly() throws {
        let options = try parseArguments(["hal", "--exclude", "Tests/**"])
        XCTAssertEqual(options.exclude, "Tests/**")
    }

    func test_explainFlag_setsShowExplanation() throws {
        let options = try parseArguments(["hal", "--explain"])
        XCTAssertTrue(options.show_explanation)
    }

    func test_verboseFlag_setsVerbose() throws {
        let options = try parseArguments(["hal", "--verbose"])
        XCTAssertTrue(options.verbose)
    }

    func test_vFlag_setsVerbose() throws {
        let options = try parseArguments(["hal", "-v"])
        XCTAssertTrue(options.verbose)
    }

    func test_summaryFormat_parsesCorrectly() throws {
        let options = try parseArguments(["hal", "--format", "summary"])
        XCTAssertEqual(options.format, .summary)
    }

    func test_positional_path_argument_parses_correctly() throws {
        let options = try parseArguments(["hal", "../../contactripple"])
        XCTAssertEqual(options.path, "../../contactripple")
    }

    func test_positional_path_with_flags_parses_correctly() throws {
        let options = try parseArguments(["hal", "Sources", "--format", "json"])
        XCTAssertEqual(options.path, "Sources")
        XCTAssertEqual(options.format, .json)
    }

    func test_path_flag_overrides_positional() throws {
        let options = try parseArguments(["hal", "Sources", "--path", "Tests"])
        XCTAssertEqual(options.path, "Tests")
    }
}
