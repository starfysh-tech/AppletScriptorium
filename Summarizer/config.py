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

DEFAULT_MODEL = "qwen3:latest"  # Ollama model for summarization
TEMPERATURE = 0.1  # Lower = more focused, higher = more creative (0.0-1.0)
MAX_TOKENS = 8192  # Maximum response length from LLM


# =============================================================================
# Performance & Parallelism
# =============================================================================

MAX_WORKERS = 5  # Concurrent article processing (balance speed vs. site load)


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


# =============================================================================
# Crawlee/Playwright Configuration (for Cloudflare-protected sites)
# =============================================================================

CRAWLEE_TIMEOUT = 60.0  # Seconds for browser-based fetching (page load)
CRAWLEE_MIN_TIMEOUT = 60.0  # Minimum timeout override for Playwright


# =============================================================================
# Domain Lists
# =============================================================================

# Sites requiring Playwright fallback due to Cloudflare/JavaScript protection
# Add domains here when standard HTTP fetching fails
CRAWLEE_DOMAINS = [
    "dailynews.ascopubs.org",
    "ascopubs.org",
    "www.urotoday.com",
    "ashpublications.org",
    "www.jacc.org",
    "www.medrxiv.org",
    "pmc.ncbi.nlm.nih.gov",
    "obgyn.onlinelibrary.wiley.com",
    "www.sciencedirect.com",
    "www.news10.com",
]

# Sites requiring non-headless browser (visible window) due to aggressive bot detection
HEADED_DOMAINS = [
    "www.news10.com",
]


# =============================================================================
# Email Templates
# =============================================================================

# Digest email subject line template
# {date} will be formatted as "%B %d, %Y" (e.g., "October 14, 2025")
DIGEST_SUBJECT_TEMPLATE = "Google Alert Intelligence — {date}"
