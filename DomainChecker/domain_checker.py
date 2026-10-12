#!/usr/bin/env python3
"""
Domain TLD Checker - Backend Server with Web UI
Run: python3 domain_checker.py
Then open: http://localhost:5000
"""

import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template_string, request, jsonify
import dns.resolver
import dns.exception
import requests
from typing import Dict, Optional
import re
import warnings
from tld_database import TLD_DATABASE, ALL_TLDS

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

app = Flask(__name__)

# Registry whois servers are slow; the 2 s DNS/HTTP timeout cut most of them off
WHOIS_TIMEOUT = 10

STATUS_ORDER = {'free': 0, 'unknown': 1, 'taken': 2}

class DomainChecker:
    def __init__(self, domain, timeout=2):
        self.domain = domain.lower()
        self.timeout = timeout

    # Each check returns True (taken), False (no sign of registration),
    # or None (the lookup failed, so nothing can be concluded).

    def check_dns(self, tld: str) -> Optional[bool]:
        """Check domain using DNS resolution"""
        full_domain = f"{self.domain}{tld}"
        resolver = dns.resolver.Resolver()
        resolver.timeout = self.timeout
        resolver.lifetime = self.timeout

        result = False
        for record_type in ('A', 'NS'):
            try:
                resolver.resolve(full_domain, record_type)
                return True
            except dns.resolver.NXDOMAIN:
                return False  # the name does not exist for any record type
            except dns.resolver.NoAnswer:
                pass
            except dns.exception.DNSException:
                result = None
        return result

    def check_http(self, tld: str) -> bool:
        """Check domain using HTTP request"""
        full_domain = f"{self.domain}{tld}"

        # Positive-only: a free domain always fails HTTP, so errors mean no hit
        for protocol in ['https', 'http']:
            try:
                response = requests.head(
                    f"{protocol}://{full_domain}",
                    timeout=self.timeout,
                    allow_redirects=False,
                    headers={'User-Agent': 'DomainChecker/1.0'},
                    verify=False
                )
                if response.status_code < 400:
                    return True
            except requests.RequestException:
                continue
        return False

    def check_whois(self, tld: str) -> Optional[bool]:
        """Check domain using whois"""
        full_domain = f"{self.domain}{tld}"
        try:
            result = subprocess.run(
                ['whois', '--', full_domain],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=WHOIS_TIMEOUT
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
        output_lower = (result.stdout + result.stderr).lower()

        # Check if available
        available_indicators = [
            'no match', 'not found', 'no entries found',
            'domain not found', 'no data found', 'status: free',
            'is available', 'no object found'
        ]
        for indicator in available_indicators:
            if indicator in output_lower:
                return False

        # Check if registered
        registered_indicators = [
            'registrar:', 'creation date:', 'expiry date:',
            'updated date:', 'domain status:', 'registrant:'
        ]
        for indicator in registered_indicators:
            if indicator in output_lower:
                return True

        # A failed run (unreachable registry server) concluded nothing
        return None if result.returncode else False

    def check_domain(self, tld: str) -> Dict:
        """Comprehensive domain check"""
        # Cheapest first; a failed lookup does not stop later checks
        results = []
        for method, check in (('DNS', self.check_dns),
                              ('HTTP', self.check_http),
                              ('WHOIS', self.check_whois)):
            found = check(tld)
            if found:
                return {'tld': tld, 'status': 'taken', 'method': method}
            results.append(found)

        if None in results:
            return {'tld': tld, 'status': 'unknown', 'method': 'UNKNOWN'}
        return {'tld': tld, 'status': 'free', 'method': 'FREE'}

@app.route('/')
def index():
    """Serve the HTML interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/check', methods=['POST'])
def check_domains():
    """API endpoint to check domain availability"""
    data = request.json
    domain = data.get('domain', '').strip().lower()
    tlds = data.get('tlds', ALL_TLDS)

    if not re.fullmatch(r'[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?', domain):
        return jsonify({'error': 'Domain must be a single label (letters, digits, hyphens)'}), 400
    if not isinstance(tlds, list):
        return jsonify({'error': 'tlds must be a list'}), 400
    tlds = [tld for tld in tlds if tld in ALL_TLDS]

    # Limit TLDs if too many
    if len(tlds) > 500:
        tlds = tlds[:500]

    checker = DomainChecker(domain, timeout=2)
    results = []

    # Check domains concurrently
    with ThreadPoolExecutor(max_workers=30) as executor:
        future_to_tld = {
            executor.submit(checker.check_domain, tld): tld
            for tld in tlds
        }

        for future in as_completed(future_to_tld):
            try:
                result = future.result()
                results.append(result)
            except Exception:
                tld = future_to_tld[future]
                results.append({
                    'tld': tld,
                    'status': 'unknown',
                    'method': 'ERROR'
                })

    # Sort results - available first, then unknown, then taken, then alphabetically
    results.sort(key=lambda x: (STATUS_ORDER[x['status']], x['tld']))

    return jsonify({
        'domain': domain,
        'total': len(results),
        'results': results
    })

# HTML Template
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Domain Finder Pro – Live Checker</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            min-height: 100vh;
            padding: 20px;
            color: #e2e8f0;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 {
            font-size: 38px;
            font-weight: 800;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 50%, #4facfe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }
        .header p { color: #94a3b8; font-size: 16px; }
        .search-section {
            background: rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 30px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .search-box {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .search-box input {
            flex: 1;
            padding: 14px 20px;
            background: rgba(255, 255, 255, 0.08);
            border: 2px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            font-size: 18px;
            color: #e2e8f0;
            transition: all 0.3s;
            min-width: 200px;
        }
        .search-box input::placeholder { color: #64748b; }
        .search-box input:focus {
            outline: none;
            border-color: #4facfe;
            background: rgba(255, 255, 255, 0.12);
            box-shadow: 0 0 0 3px rgba(79, 172, 254, 0.15);
        }
        .search-box button {
            padding: 14px 32px;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: #0f0c29;
            border: none;
            border-radius: 12px;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            white-space: nowrap;
        }
        .search-box button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px -10px rgba(79, 172, 254, 0.4);
        }
        .search-box button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .stats {
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            margin-top: 18px;
            padding-top: 18px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        }
        .stat-item { display: flex; align-items: center; gap: 8px; }
        .stat-item .number { font-weight: 700; font-size: 22px; }
        .stat-item .label { color: #94a3b8; font-size: 14px; }
        .stat-item.available .number { color: #4ade80; }
        .stat-item.taken .number { color: #f87171; }
        .stat-item.unknown .number { color: #fb923c; }
        .stat-item.total .number { color: #60a5fa; }
        .stat-item.time .number { color: #fbbf24; }

        .filters {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 20px;
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.04);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .filter-btn {
            padding: 6px 16px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            background: transparent;
            color: #94a3b8;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.3s;
            font-weight: 500;
        }
        .filter-btn:hover { border-color: #4facfe; color: #e2e8f0; }
        .filter-btn.active {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: #0f0c29;
            border-color: transparent;
            font-weight: 600;
        }

        .results-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        #unknownSection { grid-column: 1 / -1; }
        @media (max-width: 1024px) {
            .results-container { grid-template-columns: 1fr; }
        }

        .result-section {
            background: rgba(255, 255, 255, 0.04);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        .section-header h2 { font-size: 18px; display: flex; align-items: center; gap: 8px; }
        .section-header .count {
            background: rgba(255, 255, 255, 0.08);
            padding: 2px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }

        .category-group { margin-bottom: 16px; }
        .category-name {
            font-size: 12px;
            font-weight: 600;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
            padding: 4px 10px;
            background: rgba(255, 255, 255, 0.04);
            border-radius: 4px;
            display: inline-block;
        }
        .tld-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .tld-tag {
            padding: 4px 12px;
            border-radius: 8px;
            font-size: 13px;
            font-family: 'SF Mono', 'Courier New', monospace;
            transition: all 0.2s;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(255, 255, 255, 0.04);
            cursor: pointer;
            text-decoration: none;
            color: #e2e8f0;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .tld-tag:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            border-color: #4facfe;
        }
        .tld-tag.available {
            border-color: rgba(74, 222, 128, 0.3);
            background: rgba(74, 222, 128, 0.08);
            color: #4ade80;
        }
        .tld-tag.available:hover {
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.15);
        }
        .tld-tag.taken {
            border-color: rgba(248, 113, 113, 0.3);
            background: rgba(248, 113, 113, 0.08);
            color: #f87171;
        }
        .tld-tag.taken:hover {
            border-color: #f87171;
            background: rgba(248, 113, 113, 0.15);
        }
        .tld-tag.unknown {
            border-color: rgba(251, 146, 60, 0.3);
            background: rgba(251, 146, 60, 0.08);
            color: #fb923c;
        }
        .tld-tag.unknown:hover {
            border-color: #fb923c;
            background: rgba(251, 146, 60, 0.15);
        }
        .tld-tag .method-badge {
            font-size: 9px;
            padding: 1px 6px;
            border-radius: 4px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.08);
            color: #94a3b8;
        }
        .tld-tag .link-icon { font-size: 11px; opacity: 0.6; }

        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #64748b;
        }
        .empty-state .icon { font-size: 48px; margin-bottom: 10px; }

        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.2);
            border-top: 3px solid #4facfe;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .progress-container {
            margin-top: 12px;
        }
        .status-text {
            font-size: 14px;
            color: #94a3b8;
            margin-top: 6px;
        }

        .toolbar {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        .toolbar button {
            padding: 6px 14px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.04);
            color: #94a3b8;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }
        .toolbar button:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: #4facfe;
            color: #e2e8f0;
        }

        .search-history {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 12px;
        }
        .history-tag {
            padding: 4px 12px;
            background: rgba(255, 255, 255, 0.06);
            border-radius: 20px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
            color: #94a3b8;
        }
        .history-tag:hover {
            background: rgba(79, 172, 254, 0.2);
            color: #e2e8f0;
        }

        .scrollable-results {
            max-height: 500px;
            overflow-y: auto;
            padding-right: 4px;
        }
        .scrollable-results::-webkit-scrollbar {
            width: 4px;
        }
        .scrollable-results::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.04);
            border-radius: 2px;
        }
        .scrollable-results::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 2px;
        }

        .error-message {
            background: rgba(248, 113, 113, 0.1);
            border: 1px solid rgba(248, 113, 113, 0.2);
            color: #f87171;
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 15px;
        }

        @media (max-width: 640px) {
            .container { padding: 16px; }
            .search-box input { font-size: 16px; padding: 12px 16px; }
            .search-box button { font-size: 16px; padding: 12px 20px; width: 100%; }
            .header h1 { font-size: 28px; }
            .stats { gap: 12px; }
            .stat-item .number { font-size: 18px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 Domain Finder Pro</h1>
            <p>Check domain availability across 100+ TLDs with live Cloudflare links</p>
        </div>

        <div class="search-section">
            <div class="search-box">
                <input type="text" id="domainInput" placeholder="Enter domain name (e.g., replykit)" />
                <button id="searchBtn" onclick="searchDomain()">🔍 Search Domains</button>
            </div>
            <div class="search-history" id="history"></div>
            <div id="progressContainer" class="progress-container" style="display: none;">
                <div class="status-text" id="statusText">Starting scan...</div>
            </div>
            <div class="stats" id="stats" style="display: none;">
                <div class="stat-item available">
                    <span class="number" id="availableCount">0</span>
                    <span class="label">Available</span>
                </div>
                <div class="stat-item taken">
                    <span class="number" id="takenCount">0</span>
                    <span class="label">Taken</span>
                </div>
                <div class="stat-item unknown">
                    <span class="number" id="unknownCount">0</span>
                    <span class="label">Unknown</span>
                </div>
                <div class="stat-item total">
                    <span class="number" id="totalCount">0</span>
                    <span class="label">Total TLDs</span>
                </div>
                <div class="stat-item time">
                    <span class="number" id="timeCount">0s</span>
                    <span class="label">Time</span>
                </div>
            </div>
        </div>

        <div class="filters" id="filters" style="display: none;">
            <button class="filter-btn active" onclick="filterResults('all')">All</button>
            <button class="filter-btn" onclick="filterResults('available')">Available</button>
            <button class="filter-btn" onclick="filterResults('taken')">Taken</button>
            <button class="filter-btn" onclick="filterResults('unknown')">Unknown</button>
        </div>

        <div class="toolbar" id="toolbar" style="display: none;">
            <button onclick="copyResults()">📋 Copy Results</button>
            <button onclick="exportCSV()">📊 Export CSV</button>
            <button onclick="clearResults()">🗑️ Clear</button>
        </div>

        <div id="errorContainer"></div>

        <div class="results-container" id="results">
            <div class="result-section" id="availableSection">
                <div class="section-header">
                    <h2>✅ Available</h2>
                    <span class="count" id="availableCountLabel">0</span>
                </div>
                <div class="scrollable-results" id="availableResults">
                    <div class="empty-state">
                        <div class="icon">🔍</div>
                        <p>Search for a domain to see available TLDs</p>
                    </div>
                </div>
            </div>

            <div class="result-section" id="takenSection">
                <div class="section-header">
                    <h2>❌ Taken</h2>
                    <span class="count" id="takenCountLabel">0</span>
                </div>
                <div class="scrollable-results" id="takenResults">
                    <div class="empty-state">
                        <div class="icon">🔍</div>
                        <p>Search for a domain to see taken TLDs</p>
                    </div>
                </div>
            </div>

            <div class="result-section" id="unknownSection">
                <div class="section-header">
                    <h2>❓ Unknown (lookup failed)</h2>
                    <span class="count" id="unknownCountLabel">0</span>
                </div>
                <div class="scrollable-results" id="unknownResults">
                    <div class="empty-state">
                        <div class="icon">🔍</div>
                        <p>Search for a domain to see TLDs that could not be checked</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // TLD Categories - loaded from server
        let TLD_CATEGORIES = {};
        let currentResults = [];
        let currentDomain = '';
        // Same rule as the server; also drops bad entries saved by older versions
        const DOMAIN_RE = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/;
        let searchHistory = JSON.parse(localStorage.getItem('domainHistory') || '[]')
            .filter(d => typeof d === 'string' && DOMAIN_RE.test(d));

        // Fetch TLD categories from server
        async function loadTLDs() {
            try {
                const response = await fetch('/api/tlds');
                const data = await response.json();
                TLD_CATEGORIES = data;
            } catch (e) {
                console.error('Failed to load TLDs:', e);
            }
        }

        renderHistory();
        loadTLDs();

        function renderHistory() {
            const historyEl = document.getElementById('history');
            historyEl.replaceChildren(...searchHistory.map(d => {
                const tag = document.createElement('span');
                tag.className = 'history-tag';
                tag.textContent = d;
                tag.addEventListener('click', () => searchDomain(d));
                return tag;
            }));
        }

        async function searchDomain(domain) {
            const input = document.getElementById('domainInput');
            if (domain) {
                input.value = domain;
            }
            domain = input.value.trim().toLowerCase();

            if (!domain) {
                alert('Please enter a domain name');
                return;
            }
            if (!DOMAIN_RE.test(domain)) {
                alert('Domain must be a single label (letters, digits, hyphens)');
                return;
            }

            if (!searchHistory.includes(domain)) {
                searchHistory.unshift(domain);
                if (searchHistory.length > 10) searchHistory.pop();
                localStorage.setItem('domainHistory', JSON.stringify(searchHistory));
                renderHistory();
            }

            currentDomain = domain;
            await performSearch(domain);
        }

        async function performSearch(domain) {
            const btn = document.getElementById('searchBtn');
            const progressContainer = document.getElementById('progressContainer');
            const statusText = document.getElementById('statusText');
            const stats = document.getElementById('stats');
            const filters = document.getElementById('filters');
            const toolbar = document.getElementById('toolbar');
            const errorContainer = document.getElementById('errorContainer');

            btn.disabled = true;
            btn.innerHTML = '<span class="loading-spinner"></span> Searching...';
            progressContainer.style.display = 'block';
            statusText.textContent = 'Checking domains...';
            errorContainer.innerHTML = '';

            const startTime = Date.now();

            try {
                const response = await fetch('/api/check', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ domain: domain })
                });

                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                currentResults = data.results;
                displayResults(currentResults);

                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                document.getElementById('timeCount').textContent = elapsed + 's';

                statusText.textContent = '✓ Complete! Found ' + byStatus(currentResults, 'free').length + ' available domains';

                setTimeout(() => {
                    progressContainer.style.display = 'none';
                }, 2000);

                stats.style.display = 'flex';
                filters.style.display = 'flex';
                toolbar.style.display = 'flex';

            } catch (error) {
                errorContainer.innerHTML = '<div class="error-message">❌ Error: ' + error.message + '</div>';
                progressContainer.style.display = 'none';
            }

            btn.disabled = false;
            btn.innerHTML = '🔍 Search Domains';
        }

        function byStatus(results, status) {
            return results.filter(r => r.status === status);
        }

        const SECTIONS = {
            free: { id: 'availableResults', label: 'availableCountLabel', css: 'available',
                    emptyIcon: '😕', emptyText: 'No available domains found' },
            taken: { id: 'takenResults', label: 'takenCountLabel', css: 'taken',
                     emptyIcon: '🎉', emptyText: 'No taken domains found' },
            unknown: { id: 'unknownResults', label: 'unknownCountLabel', css: 'unknown',
                       emptyIcon: '✅', emptyText: 'Every TLD was checked' },
        };

        function displayResults(results) {
            document.getElementById('availableCount').textContent = byStatus(results, 'free').length;
            document.getElementById('takenCount').textContent = byStatus(results, 'taken').length;
            document.getElementById('unknownCount').textContent = byStatus(results, 'unknown').length;
            document.getElementById('totalCount').textContent = results.length;
            displaySections(results);
        }

        function displaySections(results) {
            for (const status in SECTIONS) {
                const items = byStatus(results, status);
                document.getElementById(SECTIONS[status].label).textContent = items.length;
                displaySection(status, items);
            }
        }

        function displaySection(status, results) {
            const section = SECTIONS[status];
            const container = document.getElementById(section.id);

            if (results.length === 0) {
                container.innerHTML =
                    '<div class="empty-state">' +
                        '<div class="icon">' + section.emptyIcon + '</div>' +
                        '<p>' + section.emptyText + '</p>' +
                    '</div>';
                return;
            }

            // Group by category
            const grouped = {};
            for (const category in TLD_CATEGORIES) {
                const tlds = TLD_CATEGORIES[category];
                const matched = results.filter(r => tlds.includes(r.tld));
                if (matched.length > 0) {
                    grouped[category] = matched;
                }
            }

            // Handle uncategorized
            const categorized = new Set(Object.values(TLD_CATEGORIES).flat());
            const uncategorized = results.filter(r => !categorized.has(r.tld));
            if (uncategorized.length > 0) {
                grouped['Other'] = uncategorized;
            }

            let html = '';
            for (const category in grouped) {
                const items = grouped[category];
                html += '<div class="category-group">';
                html += '<div class="category-name">' + category + ' (' + items.length + ')</div>';
                html += '<div class="tld-grid">';

                items.sort((a, b) => a.tld.localeCompare(b.tld));
                for (const item of items) {
                    const classes = 'tld-tag ' + section.css;

                    const methodBadge = status === 'free' ? '' :
                        '<span class="method-badge">' + item.method + '</span>';

                    const fullDomain = currentDomain + item.tld;
                    const cloudflareUrl = 'https://domains.cloudflare.com/?domain=' + encodeURIComponent(fullDomain);

                    html += '<a href="' + cloudflareUrl + '" target="_blank" class="' + classes + '" data-tld="' + item.tld + '">';
                    html += item.tld + ' ' + methodBadge;
                    html += ' <span class="link-icon">↗</span>';
                    html += '</a>';
                }

                html += '</div></div>';
            }

            container.innerHTML = html;
        }

        function filterResults(filter) {
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
                const btnText = btn.textContent;
                if (btnText === filter.charAt(0).toUpperCase() + filter.slice(1) ||
                    (filter === 'all' && btnText === 'All')) {
                    btn.classList.add('active');
                }
            });

            const status = { available: 'free', taken: 'taken', unknown: 'unknown' }[filter];
            displaySections(status ? byStatus(currentResults, status) : currentResults);
        }

        function copyResults() {
            const list = status => byStatus(currentResults, status).map(r => r.tld);
            const free = list('free');
            const taken = list('taken');
            const unknown = list('unknown');

            const text = 'Domain: ' + currentDomain +
                '\n\nAvailable (' + free.length + '):\n' + free.join('\n') +
                '\n\nTaken (' + taken.length + '):\n' + taken.join('\n') +
                '\n\nUnknown (' + unknown.length + '):\n' + unknown.join('\n');

            navigator.clipboard.writeText(text).then(() => {
                const btn = event.target;
                btn.textContent = '✓ Copied!';
                setTimeout(() => btn.textContent = '📋 Copy Results', 2000);
            });
        }

        function exportCSV() {
            const headers = ['TLD', 'Status', 'Method'];
            const rows = currentResults.map(r => [
                r.tld,
                { free: 'Available', taken: 'Taken', unknown: 'Unknown' }[r.status],
                r.method || 'N/A'
            ]);

            let csv = headers.join(',') + '\n';
            for (const row of rows) {
                csv += row.join(',') + '\n';
            }

            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = currentDomain + '_domains.csv';
            a.click();
            URL.revokeObjectURL(url);
        }

        function clearResults() {
            currentResults = [];
            document.getElementById('availableResults').innerHTML =
                '<div class="empty-state">' +
                    '<div class="icon">🔍</div>' +
                    '<p>Search for a domain to see available TLDs</p>' +
                '</div>';
            document.getElementById('takenResults').innerHTML =
                '<div class="empty-state">' +
                    '<div class="icon">🔍</div>' +
                    '<p>Search for a domain to see taken TLDs</p>' +
                '</div>';
            document.getElementById('unknownResults').innerHTML =
                '<div class="empty-state">' +
                    '<div class="icon">🔍</div>' +
                    '<p>Search for a domain to see TLDs that could not be checked</p>' +
                '</div>';
            document.getElementById('stats').style.display = 'none';
            document.getElementById('filters').style.display = 'none';
            document.getElementById('toolbar').style.display = 'none';
            document.getElementById('availableCountLabel').textContent = '0';
            document.getElementById('takenCountLabel').textContent = '0';
            document.getElementById('unknownCountLabel').textContent = '0';
            document.getElementById('errorContainer').innerHTML = '';
            document.getElementById('progressContainer').style.display = 'none';
        }

        document.getElementById('domainInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchDomain();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/api/tlds')
def get_tlds():
    """Return the TLD categories for the frontend"""
    return jsonify(TLD_DATABASE)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Domain Checker Web Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   🌐 Domain Finder Pro                                  ║
║                                                          ║
║   Server running at: http://{args.host}:{args.port}        ║
║   Press Ctrl+C to stop                                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)

    app.run(host=args.host, port=args.port, debug=args.debug)
