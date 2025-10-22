#!/usr/bin/env python3
"""
Chrome Extension Security Scanner

Analyzes installed Chrome extensions and generates a comprehensive CSV report
for security scanning. The scanner uses a hybrid approach:
  1. Extracts metadata from local Chrome profile manifests (fast, 100% accurate versions)
  2. Enriches missing data via Chrome Web Store scraping (developer websites, names)
  3. Generates CRXplorer-compatible CSV for security analysis

Cross-platform support: macOS, Linux, Windows

Output: extensions.csv (upload to https://crxplorer.com/)
"""

import json
import re
import csv
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

# Chrome extensions directory (works on macOS, Linux, Windows)
def get_extensions_dir():
    """Get Chrome extensions directory for current platform."""
    home = Path.home()

    # macOS
    mac_path = home / "Library/Application Support/Google/Chrome/Default/Extensions"
    if mac_path.exists():
        return mac_path

    # Linux
    linux_path = home / ".config/google-chrome/Default/Extensions"
    if linux_path.exists():
        return linux_path

    # Windows
    windows_path = home / "AppData/Local/Google/Chrome/User Data/Default/Extensions"
    if windows_path.exists():
        return windows_path

    raise FileNotFoundError("Chrome extensions directory not found")

EXTENSIONS_DIR = get_extensions_dir()

def extract_hostname(url):
    """Extract hostname from URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        hostname = parsed.netloc or parsed.path
        if hostname.startswith('www.'):
            hostname = hostname[4:]
        return hostname
    except:
        return ""

def resolve_i18n_message(message, version_dir):
    """Resolve i18n message placeholder like __MSG_appName__."""
    if not message or not message.startswith('__MSG_'):
        return message

    match = re.match(r'__MSG_(\w+)__', message)
    if not match:
        return message

    message_key = match.group(1)

    locales_path = version_dir / "_locales" / "en" / "messages.json"
    if not locales_path.exists():
        locales_path = version_dir / "locales" / "en" / "messages.json"

    if locales_path.exists():
        try:
            with open(locales_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                if message_key in messages:
                    return messages[message_key].get('message', message)
        except Exception:
            pass

    return message

def get_local_manifest_data(extension_id):
    """Extract data from local manifest.json."""
    ext_dir = EXTENSIONS_DIR / extension_id

    if not ext_dir.exists():
        return None

    version_dirs = [d for d in ext_dir.iterdir() if d.is_dir()]
    if not version_dirs:
        return None

    version_dir = version_dirs[0]
    manifest_path = version_dir / "manifest.json"

    if not manifest_path.exists():
        return None

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        name = manifest.get('name', '')
        version = manifest.get('version', '')
        homepage = manifest.get('homepage_url', '')

        # Resolve i18n message if needed
        name = resolve_i18n_message(name, version_dir)
        hostname = extract_hostname(homepage)

        return {
            'id': extension_id,
            'name': name,
            'version': version,
            'hostname': hostname,
            'has_i18n_placeholder': name.startswith('__MSG_')
        }
    except Exception as e:
        return None

def scrape_web_data(extension_id):
    """Scrape name and hostname from Chrome Web Store."""
    url = f"https://chromewebstore.google.com/detail/{extension_id}"

    try:
        result = subprocess.run(
            ['curl', '-sL', '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        html = result.stdout

        # Check if removed
        if 'item-not-found' in html.lower() or "we can't find that extension" in html.lower():
            return {'name': '404', 'hostname': ''}

        # Extract name from title
        title_match = re.search(r'<title>([^<]*)</title>', html)
        name = ''
        if title_match:
            name = title_match.group(1).replace(' - Chrome Web Store', '')

        # Extract developer website
        dev_match = re.search(r'QDHp8e">Developer</div>.*?href="(https?://[^"]+)"', html, re.DOTALL)
        hostname = ''
        if dev_match:
            url = dev_match.group(1)
            hostname = extract_hostname(url)

        return {'name': name, 'hostname': hostname}

    except Exception:
        return None

def get_installed_extension_ids():
    """Get list of installed extension IDs from Chrome profile."""
    if not EXTENSIONS_DIR.exists():
        raise FileNotFoundError(f"Chrome extensions directory not found: {EXTENSIONS_DIR}")

    extension_ids = []
    for item in EXTENSIONS_DIR.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Chrome extension IDs are 32-character lowercase letters
            if len(item.name) == 32 and item.name.isalnum():
                extension_ids.append(item.name)

    return sorted(extension_ids)

def render_progress_bar(current, total, bar_width=30):
    """Render a visual progress bar with percentage."""
    percent = int((current / total) * 100)
    filled = int((current / total) * bar_width)
    bar = '█' * filled + '░' * (bar_width - filled)
    return f"[{bar}] {current}/{total} ({percent}%)"

def main():
    output_file = "extensions.csv"

    print("Chrome Extension Security Scanner")
    print("=" * 60)
    print("Analyzes installed Chrome extensions and generates a CSV report")
    print("for security review at crxplorer.com")
    print("=" * 60)
    print()

    # Get extension IDs from Chrome profile
    try:
        extension_ids = get_installed_extension_ids()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    print(f"Scanning {len(extension_ids)} extensions from:")
    print(f"  {EXTENSIONS_DIR}")
    print()

    # Phase 1: Extract from local manifests
    print("[1/3] Extracting metadata from local manifests...")
    local_data = {}
    needs_scraping = []

    for ext_id in extension_ids:
        data = get_local_manifest_data(ext_id)
        if data:
            local_data[ext_id] = data
            # Check if we need web scraping
            if not data['hostname'] or data['has_i18n_placeholder']:
                needs_scraping.append(ext_id)
        else:
            needs_scraping.append(ext_id)

    print(f"      ✓ Found {len(local_data)} local manifests")
    if needs_scraping:
        print(f"      → {len(needs_scraping)} require web enrichment")
    print()

    # Phase 2: Web scrape only what's missing
    if needs_scraping:
        print("[2/3] Enriching from Chrome Web Store...")

        for i, ext_id in enumerate(needs_scraping, 1):
            # Render visual progress bar
            progress = render_progress_bar(i, len(needs_scraping))
            sys.stdout.write(f"\r      {progress}")
            sys.stdout.flush()

            web_data = scrape_web_data(ext_id)

            if web_data:
                # Merge with local data
                if ext_id in local_data:
                    # Use web name if local has i18n placeholder
                    if local_data[ext_id]['has_i18n_placeholder'] and web_data['name']:
                        local_data[ext_id]['name'] = web_data['name']
                    # Use web hostname if local doesn't have one
                    if not local_data[ext_id]['hostname'] and web_data['hostname']:
                        local_data[ext_id]['hostname'] = web_data['hostname']
                else:
                    # No local data, use web data entirely (no version available)
                    local_data[ext_id] = {
                        'id': ext_id,
                        'name': web_data['name'],
                        'version': '',
                        'hostname': web_data['hostname'],
                        'has_i18n_placeholder': False
                    }

        # Clear progress line and show completion
        sys.stdout.write(f"\r{' ' * 100}\r")
        print(f"      ✓ Enriched {len(needs_scraping)} extensions")
        print()
    else:
        print("[2/3] Skipping web enrichment (all data available locally)")
        print()

    # Write final CSV
    print("[3/3] Generating security scan report...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Extension ID', 'Extension Name', 'Extension version', 'Hostname'])

        for ext_id in extension_ids:
            if ext_id in local_data:
                data = local_data[ext_id]
                writer.writerow([
                    data['id'],
                    data['name'],
                    data['version'],
                    data['hostname']
                ])
            else:
                writer.writerow([ext_id, 'NOT FOUND', '', ''])

    # Summary
    complete = sum(1 for d in local_data.values() if d['name'] and d['version'] and d['hostname'])
    incomplete = [d for d in local_data.values() if not d['name'] or not d['version'] or not d['hostname']]

    print(f"      ✓ Generated {output_file}")
    print()
    print("=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print()
    print(f"Total scanned:       {len(extension_ids)} extensions")
    print(f"Complete records:    {complete} ({int(complete/len(extension_ids)*100)}%)")
    if incomplete:
        print(f"Incomplete records:  {len(incomplete)} (missing developer website)")

    print()
    print("Next Steps:")
    print(f"  1. Upload {output_file} to https://crxplorer.com/")
    print("  2. Review security findings and risk assessments")
    print("  3. Update or remove any high-risk extensions")
    print()

    return 0

if __name__ == '__main__':
    exit(main())
