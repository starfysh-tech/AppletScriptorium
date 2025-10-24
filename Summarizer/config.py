"""Configuration constants for the Google Alert Intelligence pipeline.

This module centralizes all tunable parameters. To modify behavior:
- Edit values in this file directly
- Override via environment variables where supported (ALERT_* prefix)
- See README.md and CLAUDE.md for environment variable details

Common reasons to modify:
- Model settings: Switch LLM model or adjust temperature
- Timeouts: Increase for slow sites or decrease for faster responses
- Parallelism: Adjust max_workers for different hardware
- Domain lists: Add sites requiring special browser handling
"""

# =============================================================================
# LLM Configuration
# =============================================================================

import os

# LM Studio API Configuration (Primary Backend)
# If LMSTUDIO_BASE_URL is set, LM Studio is used as primary backend
LMSTUDIO_BASE_URL = os.environ.get("LMSTUDIO_BASE_URL")  # e.g., "http://192.168.1.11:1234"
LMSTUDIO_MODEL = os.environ.get("LMSTUDIO_MODEL")  # e.g., "llama-chat-summary-3.2-3b"
LMSTUDIO_TIMEOUT = float(os.environ.get("LMSTUDIO_TIMEOUT", "30.0"))
LMSTUDIO_HEALTH_TIMEOUT = 2.0  # Fast health check timeout before requests

# Ollama Configuration (Optional Fallback Backend)
# WARNING: Ollama may significantly slow down your computer during processing
# Only enabled if OLLAMA_ENABLED=true is set in .env
OLLAMA_ENABLED = os.environ.get("OLLAMA_ENABLED", "").lower() == "true"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:latest")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120.0"))

# Legacy settings (kept for backward compatibility with tests)
DEFAULT_MODEL = OLLAMA_MODEL
TEMPERATURE = 0.1  # Lower = more focused, higher = more creative (0.0-1.0)
MAX_TOKENS = 16384  # Maximum response length from LLM


# =============================================================================
# Performance & Parallelism
# =============================================================================

# Concurrent workers for parallel article fetching and content extraction.
# Summarization runs sequentially to prevent Ollama daemon deadlock.
MAX_WORKERS = 5  # Balance speed vs. site load (fetch/extract only)


# =============================================================================
# HTTP Fetching
# =============================================================================

HTTP_TIMEOUT = 10.0  # Seconds for standard HTTP requests
MAX_RETRIES = 2  # Number of retry attempts for failed fetches

# Default HTTP headers for article fetching
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
}


# Fallback timeouts for Markdown fetchers
URLTOMD_TIMEOUT = 10.0  # Seconds for url-to-md CLI
JINA_TIMEOUT = 30.0  # Seconds for Jina Reader API


# =============================================================================
# Email Templates
# =============================================================================

# Digest email subject line template
# {date} will be formatted as "%B %d, %Y" (e.g., "October 14, 2025")
DIGEST_SUBJECT_TEMPLATE = "Google Alert Intelligence — {date}"


# =============================================================================
# Summarization Prompt
# =============================================================================

# Template for article summarization prompt sent to LLM
# Customize this to change the summary format or focus area
SUMMARY_PROMPT_TEMPLATE = """
Generate EXACTLY 4 bullets. NO MORE, NO LESS.

START IMMEDIATELY with bullet 1. NO preamble. STOP AFTER bullet 4.

Required format (output exactly this structure with one tag per bullet):
1. **KEY FINDING**: [One sentence with specific metrics/main insight]
2. **TACTICAL WIN [TAG]**: [Specific actionable practice or implementation]
3. **MARKET SIGNAL [TAG]**: [Trend, shift, or competitive development]
4. **CONCERN**: [Limitation, contradiction, or assumption to question]

Tags to use:
- TACTICAL WIN: Pick ONE of [🚀 SHIP NOW] (quick win) / [🗺️ ROADMAP] (multi-step) / [👀 WATCH] (early signal)
- MARKET SIGNAL: Pick ONE of [🔴 URGENT] (threat/deadline) / [🟡 NOTABLE] (trend) / [⚫ CONTEXT] (background)

Example output structure (use THIS article's content, not these examples):
1. **KEY FINDING**: Study shows 42% improvement in model accuracy using technique X
2. **TACTICAL WIN [🚀 SHIP NOW]**: Apply prompt engineering pattern from section 3
3. **MARKET SIGNAL [🟡 NOTABLE]**: Three competitors now using similar approach
4. **CONCERN**: Results based on single dataset; generalizability unknown

Constraints:
- Each bullet <30 words
- Include numbers/metrics from article
- Tags go INSIDE bold markers before colon
- STOP after bullet 4 - do NOT add commentary, summaries, or additional bullets
"""

# Template for cross-article insights generation
# Used to identify patterns and themes across multiple article summaries
CROSS_ARTICLE_INSIGHTS_PROMPT = """
You are analyzing {count} research articles to identify cross-cutting themes and patterns.

Articles (title + key findings):
{article_summaries}

Generate 3-5 cross-article insights that:
1. Identify recurring themes or contradictions across multiple articles (cite article numbers)
2. Highlight methodological patterns (e.g., "4 articles use PROMs to predict clinical outcomes")
3. Surface emerging trends or knowledge gaps
4. Note convergent/divergent findings

Format each insight as one line (max 50 words):
- THEME: [Pattern across N articles with evidence]
- METHODOLOGY: [Common approach across N articles]
- GAP: [Missing perspective or limitation]
- CONTRADICTION: [Conflicting findings between articles X and Y]

Requirements:
- Each insight MUST cite specific article numbers (e.g., "articles 2, 5, 8")
- Focus on actionable patterns, not generic observations
- Return 3-5 insights only
- Start directly with insights - NO preamble
"""
