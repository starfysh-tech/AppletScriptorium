import XCTest
import Foundation
@testable import SwiftHAL

final class FileDiscoveryTests: XCTestCase {

    var tempDir: URL!
    var fileManager: FileManager!

    override func setUp() {
        super.setUp()
        fileManager = FileManager.default
        tempDir = fileManager.temporaryDirectory.appendingPathComponent("SwiftHALTests-\(UUID().uuidString)")
        try! fileManager.createDirectory(at: tempDir, withIntermediateDirectories: true)
    }

    override func tearDown() {
        if let tempDir = tempDir {
            try? fileManager.removeItem(at: tempDir)
        }
        super.tearDown()
    }

    // MARK: - Default Exclusion Tests

    func test_excludes_tests_directory_by_default() throws {
        // Given: Structure with Tests directory
        let sourcesDir = tempDir.appendingPathComponent("Sources")
        let testsDir = tempDir.appendingPathComponent("Tests")
        try fileManager.createDirectory(at: sourcesDir, withIntermediateDirectories: true)
        try fileManager.createDirectory(at: testsDir, withIntermediateDirectories: true)

        let sourceFile = sourcesDir.appendingPathComponent("Main.swift")
        let testFile = testsDir.appendingPathComponent("MainTests.swift")
        try "// source".write(to: sourceFile, atomically: true, encoding: .utf8)
        try "// test".write(to: testFile, atomically: true, encoding: .utf8)

        // When: Finding files with default options
        let options = CLIOptions()
        let files = SwiftHAL.findSwiftFiles(at: tempDir, options: options, fileManager: fileManager)

        // Then: Only source file included
        XCTAssertEqual(files.count, 1)
        XCTAssertTrue(files[0].path.contains("Sources/Main.swift"))
    }

    func test_excludes_nested_tests_directory() throws {
        // Given: Nested Tests directory
        let projectDir = tempDir.appendingPathComponent("MyProject")
        let sourcesDir = projectDir.appendingPathComponent("Sources")
        let testsDir = projectDir.appendingPathComponent("Tests/MyProjectTests")
        try fileManager.createDirectory(at: sourcesDir, withIntermediateDirectories: true)
        try fileManager.createDirectory(at: testsDir, withIntermediateDirectories: true)

        let sourceFile = sourcesDir.appendingPathComponent("Code.swift")
        let testFile = testsDir.appendingPathComponent("CodeTests.swift")
        try "// source".write(to: sourceFile, atomically: true, encoding: .utf8)
        try "// test".write(to: testFile, atomically: true, encoding: .utf8)

        // When: Finding files
        let options = CLIOptions()
        let files = SwiftHAL.findSwiftFiles(at: tempDir, options: options, fileManager: fileManager)

        // Then: Test file excluded
        XCTAssertEqual(files.count, 1)
        XCTAssertTrue(files[0].path.contains("Code.swift"))
    }

    func test_excludes_tests_suffix_files() throws {
        // Given: Files ending in Tests.swift
        let dir = tempDir.appendingPathComponent("Sources")
        try fileManager.createDirectory(at: dir, withIntermediateDirectories: true)

        let regularFile = dir.appendingPathComponent("Feature.swift")
        let testFile = dir.appendingPathComponent("FeatureTests.swift")
        let unitTestFile = dir.appendingPathComponent("FeatureUnitTests.swift")
        try "// regular".write(to: regularFile, atomically: true, encoding: .utf8)
        try "// test".write(to: testFile, atomically: true, encoding: .utf8)
        try "// unit test".write(to: unitTestFile, atomically: true, encoding: .utf8)

        // When: Finding files
        let options = CLIOptions()
        let files = SwiftHAL.findSwiftFiles(at: tempDir, options: options, fileManager: fileManager)

        // Then: Only regular file included
        XCTAssertEqual(files.count, 1)
        XCTAssertTrue(files[0].path.hasSuffix("Feature.swift"))
        XCTAssertFalse(files[0].lastPathComponent.contains("Tests"))
    }

    func test_excludes_package_swift() throws {
        // Given: Package.swift file
        let packageFile = tempDir.appendingPathComponent("Package.swift")
        let sourceFile = tempDir.appendingPathComponent("Sources/Main.swift")
        try fileManager.createDirectory(at: sourceFile.deletingLastPathComponent(), withIntermediateDirectories: true)
        try "// package".write(to: packageFile, atomically: true, encoding: .utf8)
        try "// source".write(to: sourceFile, atomically: true, encoding: .utf8)

        // When: Finding files
        let options = CLIOptions()
        let files = SwiftHAL.findSwiftFiles(at: tempDir, options: options, fileManager: fileManager)

        // Then: Package.swift excluded
        XCTAssertEqual(files.count, 1)
        XCTAssertTrue(files[0].path.contains("Main.swift"))
        XCTAssertFalse(files.contains(where: { $0.lastPathComponent == "Package.swift" }))
    }

    // MARK: - Include Tests Flag Tests

    func test_include_tests_flag_includes_tests_directory() throws {
        // Given: Structure with Tests directory
        let sourcesDir = tempDir.appendingPathComponent("Sources")
        let testsDir = tempDir.appendingPathComponent("Tests")
        try fileManager.createDirectory(at: sourcesDir, withIntermediateDirectories: true)
        try fileManager.createDirectory(at: testsDir, withIntermediateDirectories: true)

        let sourceFile = sourcesDir.appendingPathComponent("Main.swift")
        let testFile = testsDir.appendingPathComponent("MainTests.swift")
        try "// source".write(to: sourceFile, atomically: true, encoding: .utf8)
        try "// test".write(to: testFile, atomically: true, encoding: .utf8)

        // When: Finding files with include_tests flag
        var options = CLIOptions()
        options.include_tests = true
        let files = SwiftHAL.findSwiftFiles(at: tempDir, options: options, fileManager: fileManager)

        // Then: Both files included
        XCTAssertEqual(files.count, 2)
        XCTAssertTrue(files.contains(where: { $0.path.contains("Main.swift") }))
        XCTAssertTrue(files.contains(where: { $0.path.contains("MainTests.swift") }))
    }

    func test_include_tests_flag_includes_tests_suffix() throws {
        // Given: Files ending in Tests.swift
        let dir = tempDir.appendingPathComponent("Sources")
        try fileManager.createDirectory(at: dir, withIntermediateDirectories: true)

        let regularFile = dir.appendingPathComponent("Feature.swift")
        let testFile = dir.appendingPathComponent("FeatureTests.swift")
        try "// regular".write(to: regularFile, atomically: true, encoding: .utf8)
        try "// test".write(to: testFile, atomically: true, encoding: .utf8)

        // When: Finding files with include_tests flag
        var options = CLIOptions()
        options.include_tests = true
        let files = SwiftHAL.findSwiftFiles(at: tempDir, options: options, fileManager: fileManager)

        // Then: Both files included
        XCTAssertEqual(files.count, 2)
    }

    func test_include_tests_flag_still_excludes_package_swift() throws {
        // Given: Package.swift and test files
        let packageFile = tempDir.appendingPathComponent("Package.swift")
        let testFile = tempDir.appendingPathComponent("Tests/MainTests.swift")
        try fileManager.createDirectory(at: testFile.deletingLastPathComponent(), withIntermediateDirectories: true)
        try "// package".write(to: packageFile, atomically: true, encoding: .utf8)
        try "// test".write(to: testFile, atomically: true, encoding: .utf8)

        // When: Finding files with include_tests flag
        var options = CLIOptions()
        options.include_tests = true
        let files = SwiftHAL.findSwiftFiles(at: tempDir, options: options, fileManager: fileManager)

        // Then: Test included, Package.swift excluded
        XCTAssertEqual(files.count, 1)
        XCTAssertTrue(files[0].path.contains("MainTests.swift"))
        XCTAssertFalse(files.contains(where: { $0.lastPathComponent == "Package.swift" }))
    }

    // MARK: - Edge Cases

    func test_excludes_case_variations() throws {
        // Given: Various case patterns
        let dir = tempDir.appendingPathComponent("Sources")
        try fileManager.createDirectory(at: dir, withIntermediateDirectories: true)

        let regularFile = dir.appendingPathComponent("Feature.swift")
        let testFile = dir.appendingPathComponent("FeatureTests.swift")
        let singularTestFile = dir.appendingPathComponent("FeatureTest.swift")
        try "// regular".write(to: regularFile, atomically: true, encoding: .utf8)
        try "// test".write(to: testFile, atomically: true, encoding: .utf8)
        try "// singular".write(to: singularTestFile, atomically: true, encoding: .utf8)

        // When: Finding files
        let options = CLIOptions()
        let found = SwiftHAL.findSwiftFiles(at: tempDir, options: options, fileManager: fileManager)

        // Then: Only non-Tests.swift files included
        XCTAssertEqual(found.count, 2, "Expected Feature.swift and FeatureTest.swift")
        XCTAssertTrue(found.contains(where: { $0.lastPathComponent == "Feature.swift" }))
        XCTAssertTrue(found.contains(where: { $0.lastPathComponent == "FeatureTest.swift" }))
        XCTAssertFalse(found.contains(where: { $0.lastPathComponent == "FeatureTests.swift" }))
    }

    func test_excludes_deeply_nested_tests() throws {
        // Given: Deeply nested Tests directories
        let deepTestDir = tempDir.appendingPathComponent("Project/Sub1/Sub2/Tests/Unit")
        let sourceDir = tempDir.appendingPathComponent("Project/Sources")
        try fileManager.createDirectory(at: deepTestDir, withIntermediateDirectories: true)
        try fileManager.createDirectory(at: sourceDir, withIntermediateDirectories: true)

        let testFile = deepTestDir.appendingPathComponent("DeepTests.swift")
        let sourceFile = sourceDir.appendingPathComponent("Source.swift")
        try "// test".write(to: testFile, atomically: true, encoding: .utf8)
        try "// source".write(to: sourceFile, atomically: true, encoding: .utf8)

        // When: Finding files
        let options = CLIOptions()
        let files = SwiftHAL.findSwiftFiles(at: tempDir, options: options, fileManager: fileManager)

        // Then: Deep test excluded
        XCTAssertEqual(files.count, 1)
        XCTAssertTrue(files[0].path.contains("Source.swift"))
    }
}
