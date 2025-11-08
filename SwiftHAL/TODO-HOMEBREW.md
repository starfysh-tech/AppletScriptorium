# TODO: Homebrew Packaging for SwiftHAL

## Overview

This document outlines the steps to make SwiftHAL available via Homebrew package manager.

**Approach:** Create a custom tap (`homebrew-swifthal`) for initial release, with potential migration to homebrew-core after proven stability.

---

## Prerequisites

- [ ] SwiftHAL has stable release (v2.1.0 or later)
- [ ] GitHub repository is public
- [ ] LICENSE file exists (MIT)
- [ ] All tests passing
- [ ] Documentation complete

---

## Step 1: Tag and Release

### 1.1 Create Git Tag

```bash
cd /Users/randallnoval/Code/AppletScriptorium/SwiftHAL

# Tag the release
git tag -a v2.1.0 -m "Release v2.1.0: Staff-level refactoring complete"
git push origin v2.1.0
```

### 1.2 Get Commit SHA

```bash
# Get the commit SHA for the tag
git rev-parse v2.1.0

# Save this SHA - you'll need it for the formula
```

### 1.3 Create GitHub Release

**Option A: Manual (GitHub Web UI)**
1. Go to https://github.com/starfysh-tech/AppletScriptorium/releases
2. Click "Draft a new release"
3. Select tag: `v2.1.0`
4. Title: "SwiftHAL v2.1.0"
5. Description: Copy from release notes
6. Publish release

**Option B: Automated (gh CLI)**
```bash
gh release create v2.1.0 \
  --title "SwiftHAL v2.1.0" \
  --notes "See CHANGELOG.md for details"
```

---

## Step 2: Create Tap Repository

### 2.1 Create Repository

```bash
# Create new directory
mkdir ~/homebrew-swifthal
cd ~/homebrew-swifthal

# Initialize structure
mkdir Formula
touch README.md
git init
```

### 2.2 Create Formula

Create `Formula/swifthal.rb`:

```ruby
class Swifthal < Formula
  desc "Swift CLI tool for calculating Halstead complexity metrics"
  homepage "https://github.com/starfysh-tech/AppletScriptorium/tree/main/SwiftHAL"
  url "https://github.com/starfysh-tech/AppletScriptorium.git",
      tag:      "v2.1.0",
      revision: "REPLACE_WITH_COMMIT_SHA_FROM_STEP_1.2"
  license "MIT"
  head "https://github.com/starfysh-tech/AppletScriptorium.git", branch: "main"

  depends_on macos: :ventura
  depends_on xcode: ["14.0", :build]

  def install
    cd "SwiftHAL" do
      system "swift", "build", "--disable-sandbox", "-c", "release", "--product", "SwiftHAL"
      bin.install ".build/release/SwiftHAL" => "hal"
    end
  end

  test do
    # Version/help check
    assert_match "SwiftHAL", shell_output("#{bin}/hal --help")

    # Functional test
    (testpath/"Sample.swift").write <<~EOS
      import Foundation

      func calculateSum(a: Int, b: Int) -> Int {
        return a + b
      }
    EOS

    output = shell_output("#{bin}/hal --path #{testpath}/Sample.swift --format json")
    assert_match "volume", output
    assert_match "difficulty", output
  end
end
```

**Important:** Replace `REPLACE_WITH_COMMIT_SHA_FROM_STEP_1.2` with actual SHA.

### 2.3 Create README

Create `README.md`:

```markdown
# Homebrew SwiftHAL

Homebrew tap for [SwiftHAL](https://github.com/starfysh-tech/AppletScriptorium/tree/main/SwiftHAL), a Swift CLI tool for calculating Halstead complexity metrics.

## Installation

```bash
brew tap starfysh-tech/swifthal
brew install swifthal
```

## Usage

```bash
hal --path /path/to/swift/project
```

See [SwiftHAL documentation](https://github.com/starfysh-tech/AppletScriptorium/tree/main/SwiftHAL) for full usage guide.

## Updating

```bash
brew upgrade swifthal
```

## Uninstall

```bash
brew uninstall swifthal
brew untap starfysh-tech/swifthal
```
```

### 2.4 Publish Tap

```bash
cd ~/homebrew-swifthal

# Create GitHub repository first (web UI or gh CLI)
gh repo create starfysh-tech/homebrew-swifthal --public

# Push tap
git add .
git commit -m "Add swifthal formula v2.1.0"
git remote add origin https://github.com/starfysh-tech/homebrew-swifthal.git
git push -u origin main
```

---

## Step 3: Test Installation

### 3.1 Local Testing

```bash
# Test from local directory first
brew tap starfysh-tech/swifthal ~/homebrew-swifthal
brew install --build-from-source swifthal
brew test swifthal
```

### 3.2 Verify Installation

```bash
# Check binary installed
which hal
# Should show: /usr/local/bin/hal or /opt/homebrew/bin/hal

# Test functionality
hal --help
hal --path /path/to/swift/project
```

### 3.3 Test from Published Tap

```bash
# Remove local tap
brew untap starfysh-tech/swifthal
brew uninstall swifthal

# Install from GitHub
brew tap starfysh-tech/swifthal
brew install swifthal
```

---

## Step 4: Validate Formula

### 4.1 Audit Formula

```bash
brew audit --strict --online swifthal
```

Fix any warnings or errors reported.

### 4.2 Test Formula

```bash
brew test swifthal
```

Should output: `Testing swifthal... ✓`

---

## Step 5: Update SwiftHAL Documentation

### 5.1 Add Homebrew Installation to README

In `SwiftHAL/README.md`, add installation section:

```markdown
## Installation

### Homebrew (macOS)

```bash
brew tap starfysh-tech/swifthal
brew install swifthal
```

### Manual Installation

```bash
git clone https://github.com/starfysh-tech/AppletScriptorium.git
cd AppletScriptorium/SwiftHAL
swift build -c release
cp .build/release/SwiftHAL /usr/local/bin/hal
```
```

---

## Updating the Formula (Future Releases)

When releasing new versions:

1. **Tag new version:**
   ```bash
   git tag -a v1.1.0 -m "Release v1.1.0"
   git push origin v1.1.0
   ```

2. **Get new commit SHA:**
   ```bash
   git rev-parse v1.1.0
   ```

3. **Update formula:**
   ```bash
   cd ~/homebrew-swifthal
   # Edit Formula/swifthal.rb
   # Update 'tag' and 'revision' fields
   git add Formula/swifthal.rb
   git commit -m "Update swifthal to v1.1.0"
   git push
   ```

4. **Users upgrade:**
   ```bash
   brew update
   brew upgrade swifthal
   ```

---

## Future Enhancements

### Option 1: Add Bottles (Pre-built Binaries)

**Benefits:**
- Faster installation (no compilation needed)
- Better user experience

**Implementation:**
- Use GitHub Actions to build binaries for different macOS versions
- Generate bottle DSL for formula
- Upload bottles to GitHub releases

**Reference:** https://docs.brew.sh/Bottles

### Option 2: Submit to homebrew-core

**When:**
- After 6+ months of stability
- Multiple versions released (3+)
- Active maintenance demonstrated
- Notable user adoption

**Process:**
1. Fork https://github.com/Homebrew/homebrew-core
2. Copy formula to `Formula/s/swifthal.rb`
3. Update formula per homebrew-core guidelines
4. Submit pull request
5. Address maintainer feedback

**Benefits:**
- `brew install swifthal` (no tap needed)
- Wider discoverability
- Official Homebrew catalog

**Reference:** https://docs.brew.sh/How-To-Open-a-Homebrew-Pull-Request

---

## Troubleshooting

### Build Fails

```bash
# Check build manually
cd /tmp
git clone https://github.com/starfysh-tech/AppletScriptorium.git
cd AppletScriptorium/SwiftHAL
swift build -c release --product SwiftHAL
```

### Test Fails

```bash
# Run formula test with verbose output
brew test --verbose swifthal
```

### Installation Issues

```bash
# Clean cache and reinstall
brew cleanup swifthal
brew uninstall swifthal
brew install --build-from-source swifthal
```

---

## Resources

- **Homebrew Formula Cookbook:** https://docs.brew.sh/Formula-Cookbook
- **Homebrew Taps:** https://docs.brew.sh/Taps
- **Swift Formulas Reference:**
  - SwiftLint: https://github.com/Homebrew/homebrew-core/blob/master/Formula/s/swiftlint.rb
  - swift-format: https://github.com/Homebrew/homebrew-core/blob/master/Formula/s/swift-format.rb
- **Homebrew Best Practices:** https://docs.brew.sh/Formulae-Best-Practices
