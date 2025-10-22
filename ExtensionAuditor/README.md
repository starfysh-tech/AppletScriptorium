# ExtensionAuditor

Security scanner for Chrome/Chromium extensions. Analyzes installed extensions and generates comprehensive CSV reports for vulnerability scanning on CRXplorer.

## What It Does

- **Scans** all installed Chrome extensions from your local profile
- **Extracts** metadata: extension ID, name, version, developer website
- **Enriches** missing data via Chrome Web Store (when needed)
- **Generates** CRXplorer-compatible CSV for security analysis

## Quick Start

```bash
cd ExtensionAuditor
./extension-auditor.py
```

Output: `extensions.csv` ready for upload to https://crxplorer.com/

## How It Works

ExtensionAuditor uses a hybrid approach for maximum speed and accuracy:

### Phase 1: Local Manifest Extraction
Reads extension metadata directly from Chrome's local storage:
- Fast: No network requests
- Accurate: 100% reliable version numbers
- Complete: All installed extensions discovered

### Phase 2: Web Enrichment (When Needed)
For extensions missing developer websites or internationalized names, fetches data from Chrome Web Store:
- Targeted: Only enriches incomplete records
- Visual progress: Real-time progress bar
- Efficient: Processes ~60 extensions in ~30 seconds

### Phase 3: CSV Generation
Creates CRXplorer-compatible report with:
- Extension ID (unique identifier)
- Extension Name (resolved from i18n placeholders)
- Version (from local manifest)
- Developer Website (hostname only)

## Output

### extensions.csv
```csv
Extension ID,Extension Name,Extension version,Hostname
fmkadmapgofadopljbjfkapdkoienihi,React Developer Tools,7.0.1,dnb.com
nngceckbapebfimnlniiiahkandclblb,Bitwarden Password Manager,2025.9.0,bitwarden.com
```

**Format:** CRXplorer-compatible CSV (upload directly to security scanner)

## Next Steps

After generating the CSV:

1. **Upload** to https://crxplorer.com/ for security analysis
2. **Review** findings: vulnerability reports, permission analysis, malware detection
3. **Action** on risks: update outdated extensions, remove suspicious ones

## Requirements

- **Python:** 3.11+ (standard library only, no external dependencies)
- **Browser:** Chrome or Chromium installed with extensions
- **Internet:** Required for web enrichment phase
- **Platform:** macOS, Linux, or Windows

## Platform Support

ExtensionAuditor automatically detects your Chrome extensions directory:

- **macOS:** `~/Library/Application Support/Google/Chrome/Default/Extensions`
- **Linux:** `~/.config/google-chrome/Default/Extensions`
- **Windows:** `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Extensions`

## Usage Examples

### Basic Scan
```bash
./extension-auditor.py
```

### Python Invocation
```bash
python3 extension-auditor.py
```

### Check Results
```bash
# View first 10 extensions
head -10 extensions.csv

# Count total extensions
wc -l extensions.csv
```

## Sample Output

```
Chrome Extension Security Scanner
============================================================
Analyzes installed Chrome extensions and generates a CSV report
for security review at crxplorer.com
============================================================

Scanning 72 extensions from:
  /Users/randall/Library/Application Support/Google/Chrome/Default/Extensions

[1/3] Extracting metadata from local manifests...
      ✓ Found 72 local manifests
      → 55 require web enrichment

[2/3] Enriching from Chrome Web Store...
      [██████████████████████████████] 55/55 (100%)
      ✓ Enriched 55 extensions

[3/3] Generating security scan report...
      ✓ Generated extensions.csv

============================================================
SCAN COMPLETE
============================================================

Total scanned:       72 extensions
Complete records:    70 (97%)
Incomplete records:  2 (missing developer website)

Next Steps:
  1. Upload extensions.csv to https://crxplorer.com/
  2. Review security findings and risk assessments
  3. Update or remove any high-risk extensions
```

## Technical Details

### Hybrid Extraction Strategy

**Local-first approach:**
- Reads `manifest.json` from each extension directory
- Resolves i18n message placeholders (`__MSG_appName__`) from locale files
- Extracts version numbers (100% accurate from local data)

**Web enrichment (only when needed):**
- Scrapes Chrome Web Store for missing developer websites
- Resolves unresolved i18n placeholders
- Typically needed for ~75% of extensions

**Performance:**
- Local extraction: <1 second for 100+ extensions
- Web enrichment: ~0.5 seconds per extension (parallel processing planned)
- Total time: ~30-60 seconds for typical installation

### Cross-Platform Compatibility

Uses `Path.home()` for platform-independent home directory detection. Automatically selects correct Chrome extensions path based on OS.

### Data Privacy

- **Local-first:** Prioritizes local manifest data
- **Minimal web requests:** Only fetches missing developer websites
- **No tracking:** No data sent to external services (except Chrome Web Store for enrichment)
- **Read-only:** Never modifies Chrome profile or extension files

## Troubleshooting

### "Chrome extensions directory not found"
- Ensure Chrome/Chromium is installed
- Verify you have extensions installed (check `chrome://extensions`)
- Check non-default profile locations manually

### Incomplete Records
Some extensions legitimately lack developer websites in both local manifests and Chrome Web Store listings. This is common for:
- Built-in Chrome components
- Deprecated/unlisted extensions
- Developer tools without public websites

These extensions can still be uploaded to CRXplorer for analysis.

### Slow Web Enrichment
Web enrichment speed depends on:
- Network latency to Chrome Web Store
- Number of extensions requiring enrichment
- Chrome Web Store server response times

Typical rate: ~2 extensions/second

## Future Enhancements

Planned improvements:
- Parallel web scraping (5x faster enrichment)
- Browser profile selection (--profile flag)
- JSON output format option
- Offline mode (skip web enrichment)
- Extension risk scoring (local heuristics)

## Contributing

ExtensionAuditor is part of the AppletScriptorium automation framework. See the main repository for contribution guidelines.

## License

See repository root for license information.
