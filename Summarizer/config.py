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
LMSTUDIO_TIMEOUT = float(os.environ.get("LMSTUDIO_TIMEOUT", "180.0"))
LMSTUDIO_HEALTH_TIMEOUT = 2.0  # Fast health check timeout before requests

# Ollama Configuration (Optional Fallback Backend)
# WARNING: Ollama may significantly slow down your computer during processing
# Only enabled if OLLAMA_ENABLED=true is set in .env
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_ENABLED = os.environ.get("OLLAMA_ENABLED", "").lower() == "true"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:latest")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120.0"))

# Legacy settings (kept for backward compatibility with tests)
DEFAULT_MODEL = OLLAMA_MODEL
TEMPERATURE = 0.1  # Lower = more focused, higher = more creative (0.0-1.0)
MAX_TOKENS = 16384  # Maximum response length from LLM

# Content truncation to fit model context window
# 40,000 chars ≈ 10,000 tokens, leaves ~6,000 tokens for prompt + response
MAX_CONTENT_CHARS = int(os.environ.get("MAX_CONTENT_CHARS", "40000"))


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
# {topic} is the Google Alert topic from the email subject
# {count} is the number of articles in the digest
DIGEST_SUBJECT_TEMPLATE = "Google Alert Intelligence: {topic} ({count} articles) — {date}"


# =============================================================================
# Article Classification
# =============================================================================

# Prompt to classify article type before summarization
ARTICLE_TYPE_PROMPT = """Classify this article as ONE of these types:
- RESEARCH: Academic paper, study, clinical trial, methodology paper
- NEWS: Journalist-written story about current events, third-party reporting
- OPINION: Editorial, analysis, commentary, prediction, thought piece
- PRESS_RELEASE: Company-issued announcement (look for: stock ticker like OTC/NYSE/NASDAQ,
  CEO/executive quotes, "sponsored content", "PR Newswire", "Business Wire", "EQS-News",
  company name in headline, first-person "we" language)

Return ONLY the type name (e.g., "PRESS_RELEASE"), nothing else.

Article content:
{content}
"""

# Valid article types
ARTICLE_TYPES = ["RESEARCH", "NEWS", "OPINION", "PRESS_RELEASE"]


# =============================================================================
# Summarization Prompts
# =============================================================================

# Default summarization prompt (used when type detection fails or for backward compatibility)
SUMMARY_PROMPT_TEMPLATE = """
Generate EXACTLY 4 bullets. NO MORE, NO LESS.

START IMMEDIATELY with bullet 1. NO preamble. STOP AFTER bullet 4.

Required format (output exactly this structure with one tag per bullet):
1. **KEY FINDING**: [One sentence with specific metrics/main insight]
2. **TACTICAL WIN [TAG]**: [Specific actionable practice or implementation]
3. **MARKET SIGNAL [TAG]**: [Trend, shift, or competitive development]
4. **CONCERN**: [ONLY if article EXPLICITLY states a risk, limitation, or negative outcome. Otherwise write EXACTLY: "No concerns stated in article."]

CONCERN RULES (CRITICAL):
- DO NOT invent concerns not in the article
- DO NOT list benefits as concerns (e.g., "better adherence" is a BENEFIT)
- DO NOT speculate about potential issues (e.g., "may raise privacy concerns" unless article says this)
- ONLY quote or paraphrase concerns the author explicitly wrote

Tags to use:
- TACTICAL WIN: Pick ONE of [🚀 SHIP NOW] (quick win) / [🗺️ ROADMAP] (multi-step) / [👀 WATCH] (early signal)
- MARKET SIGNAL: Pick ONE of [🔴 URGENT] (threat/deadline) / [🟡 NOTABLE] (trend) / [⚫ CONTEXT] (background)

Example output structure:
1. **KEY FINDING**: [State main finding with specific metrics from article]
2. **TACTICAL WIN [🚀/🗺️/👀]**: [Describe actionable practice from article]
3. **MARKET SIGNAL [🔴/🟡/⚫]**: [Identify trend or development from article]
4. **CONCERN**: [Quote or paraphrase specific concern FROM article, or "No significant concerns identified in article."]

Constraints:
- Each bullet <30 words
- Include numbers/metrics from article
- Tags go INSIDE bold markers before colon
- STOP after bullet 4 - do NOT add commentary, summaries, or additional bullets

After the 4 bullets, add exactly one line in this format:
**ACTIONABILITY**: <emoji> <label>

Choose ONE based on urgency:
- 🎯 ACT NOW = Urgent deadline, competitive threat, immediate opportunity
- ⚠️ MONITOR = Emerging trend, ongoing development, watch item
- 🔍 RESEARCH NEEDED = Unclear implications, needs more data
- ℹ️ CONTEXT ONLY = Background info, historical context

Example: **ACTIONABILITY**: ⚠️ MONITOR

Output as JSON:
{"bullets": [{"label": "KEY FINDING", "text": "..."}, {"label": "TACTICAL WIN [🚀/🗺️/👀]", "text": "..."}, {"label": "MARKET SIGNAL [🔴/🟡/⚫]", "text": "..."}, {"label": "CONCERN", "text": "..."}], "actionability": {"emoji": "⚠️", "label": "MONITOR"}}
"""

# Type-specific prompt variants for different article types
SUMMARY_PROMPTS = {
    "RESEARCH": """Generate EXACTLY 4 bullets. NO MORE, NO LESS.

START IMMEDIATELY with bullet 1. NO preamble. STOP AFTER bullet 4.

Required format:
1. **KEY FINDING**: [Main result with sample size, p-value, or confidence interval if mentioned]
2. **METHODOLOGY**: [Study design, population, duration, limitations acknowledged by authors]
3. **IMPLICATION**: [What this means for practice, policy, or future research]
4. **CONCERN**: [ONLY if article EXPLICITLY states a methodological flaw, funding bias, or limitation. Otherwise write EXACTLY: "No concerns stated in article."]

CONCERN RULES (CRITICAL):
- DO NOT invent concerns not in the article
- DO NOT list benefits as concerns
- ONLY quote or paraphrase concerns the authors explicitly wrote

Constraints:
- Each bullet <30 words
- Include specific metrics from article
- STOP after bullet 4 - do NOT add commentary

After the 4 bullets, add exactly one line in this format:
**ACTIONABILITY**: <emoji> <label>

Choose ONE based on urgency:
- 🎯 ACT NOW = Urgent deadline, competitive threat, immediate opportunity
- ⚠️ MONITOR = Emerging trend, ongoing development, watch item
- 🔍 RESEARCH NEEDED = Unclear implications, needs more data
- ℹ️ CONTEXT ONLY = Background info, historical context

Example: **ACTIONABILITY**: ⚠️ MONITOR

Output as JSON:
{"bullets": [{"label": "KEY FINDING", "text": "..."}, {"label": "METHODOLOGY", "text": "..."}, {"label": "IMPLICATION", "text": "..."}, {"label": "CONCERN", "text": "..."}], "actionability": {"emoji": "⚠️", "label": "MONITOR"}}
""",

    "NEWS": """Generate EXACTLY 4 bullets. NO MORE, NO LESS.

START IMMEDIATELY with bullet 1. NO preamble. STOP AFTER bullet 4.

Required format:
1. **KEY DEVELOPMENT**: [What happened, when, who is affected, with specific dates/numbers]
2. **TACTICAL WIN [TAG]**: [Actionable response or opportunity. TAG: 🚀 SHIP NOW / 🗺️ ROADMAP / 👀 WATCH]
3. **MARKET SIGNAL [TAG]**: [Trend or competitive implication. TAG: 🔴 URGENT / 🟡 NOTABLE / ⚫ CONTEXT]
4. **CONCERN**: [ONLY if article EXPLICITLY states a risk or uncertainty. Otherwise write EXACTLY: "No concerns stated in article."]

CONCERN RULES (CRITICAL):
- DO NOT invent concerns not in the article
- DO NOT list benefits as concerns
- DO NOT speculate about potential issues
- ONLY quote or paraphrase concerns explicitly stated in article

Constraints:
- Each bullet <30 words
- Include specific dates, numbers, or names from article
- Tags go INSIDE bold markers before colon
- STOP after bullet 4 - do NOT add commentary

After the 4 bullets, add exactly one line in this format:
**ACTIONABILITY**: <emoji> <label>

Choose ONE based on urgency:
- 🎯 ACT NOW = Urgent deadline, competitive threat, immediate opportunity
- ⚠️ MONITOR = Emerging trend, ongoing development, watch item
- 🔍 RESEARCH NEEDED = Unclear implications, needs more data
- ℹ️ CONTEXT ONLY = Background info, historical context

Example: **ACTIONABILITY**: ⚠️ MONITOR

Output as JSON:
{"bullets": [{"label": "KEY DEVELOPMENT", "text": "..."}, {"label": "TACTICAL WIN [🚀/🗺️/👀]", "text": "..."}, {"label": "MARKET SIGNAL [🔴/🟡/⚫]", "text": "..."}, {"label": "CONCERN", "text": "..."}], "actionability": {"emoji": "⚠️", "label": "MONITOR"}}
""",

    "PRESS_RELEASE": """Generate EXACTLY 4 bullets. NO MORE, NO LESS.

START IMMEDIATELY with bullet 1. NO preamble. STOP AFTER bullet 4.

Required format:
1. **ANNOUNCEMENT**: [What was announced, key metrics, specific numbers]
2. **STRATEGIC MOVE**: [Why this matters competitively, market positioning]
3. **TIMELINE**: [When this takes effect, next steps, key dates mentioned]
4. **CONCERN**: [ONLY if release EXPLICITLY states a caveat, risk, or limitation. Otherwise write EXACTLY: "No concerns stated in article."]

CONCERN RULES (CRITICAL):
- DO NOT invent concerns not in the release
- DO NOT list benefits as concerns (e.g., "better outcomes" is a BENEFIT)
- DO NOT speculate (e.g., "may raise privacy concerns" unless release says this)
- ONLY quote or paraphrase concerns explicitly stated in the release

Constraints:
- Each bullet <30 words
- Include specific metrics/dates from release
- STOP after bullet 4 - do NOT add commentary

After the 4 bullets, add exactly one line in this format:
**ACTIONABILITY**: <emoji> <label>

Choose ONE based on urgency:
- 🎯 ACT NOW = Urgent deadline, competitive threat, immediate opportunity
- ⚠️ MONITOR = Emerging trend, ongoing development, watch item
- 🔍 RESEARCH NEEDED = Unclear implications, needs more data
- ℹ️ CONTEXT ONLY = Background info, historical context

Example: **ACTIONABILITY**: ⚠️ MONITOR

Output as JSON:
{"bullets": [{"label": "ANNOUNCEMENT", "text": "..."}, {"label": "STRATEGIC MOVE", "text": "..."}, {"label": "TIMELINE", "text": "..."}, {"label": "CONCERN", "text": "..."}], "actionability": {"emoji": "⚠️", "label": "MONITOR"}}
""",

    "OPINION": """Generate EXACTLY 4 bullets. NO MORE, NO LESS.

START IMMEDIATELY with bullet 1. NO preamble. STOP AFTER bullet 4.

Required format:
1. **THESIS**: [Author's main argument in one clear sentence]
2. **EVIDENCE**: [Key supporting points, data, or examples cited]
3. **COUNTERPOINT**: [Acknowledged limitations, opposing views, or nuances]
4. **CREDIBILITY**: [Author expertise, publication reputation, evidence strength. If no credibility concerns, write: "No credibility concerns identified."]

CREDIBILITY RULES (CRITICAL):
- DO NOT invent credibility issues not evident in the article
- DO NOT speculate about author bias without evidence
- ONLY note issues explicitly apparent from the article

Constraints:
- Each bullet <30 words
- Distinguish between author's claims and supporting evidence
- STOP after bullet 4 - do NOT add commentary

After the 4 bullets, add exactly one line in this format:
**ACTIONABILITY**: <emoji> <label>

Choose ONE based on urgency:
- 🎯 ACT NOW = Urgent deadline, competitive threat, immediate opportunity
- ⚠️ MONITOR = Emerging trend, ongoing development, watch item
- 🔍 RESEARCH NEEDED = Unclear implications, needs more data
- ℹ️ CONTEXT ONLY = Background info, historical context

Example: **ACTIONABILITY**: ⚠️ MONITOR

Output as JSON:
{"bullets": [{"label": "THESIS", "text": "..."}, {"label": "EVIDENCE", "text": "..."}, {"label": "COUNTERPOINT", "text": "..."}, {"label": "CREDIBILITY", "text": "..."}], "actionability": {"emoji": "⚠️", "label": "MONITOR"}}
"""
}


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

# Cross-article insight gates (skip insights if thresholds not met)
CROSS_ARTICLE_MIN_ARTICLES = int(os.environ.get("CROSS_ARTICLE_MIN_ARTICLES", "3"))
CROSS_ARTICLE_MIN_SOURCES = int(os.environ.get("CROSS_ARTICLE_MIN_SOURCES", "2"))


# =============================================================================
# Structured Output Schema (LM Studio)
# =============================================================================

# JSON schema to enforce structured summary output
# See: https://lmstudio.ai/docs/advanced/structured-output
SUMMARY_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "article_summary",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "bullets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "text": {"type": "string"}
                        },
                        "required": ["label", "text"]
                    },
                    "minItems": 4,
                    "maxItems": 4
                },
                "actionability": {
                    "type": "object",
                    "properties": {
                        "emoji": {"type": "string"},
                        "label": {"type": "string"}
                    },
                    "required": ["emoji", "label"]
                }
            },
            "required": ["bullets", "actionability"]
        }
    }
}
