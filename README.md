# AppletScriptorium — macOS Automation Tools

AppletScriptorium is a collection of practical automation tools that solve real workflow problems on macOS. Each tool is built with simplicity, local execution, and user control in mind.

## Strategy & Goals

**Philosophy:** Build simple, focused tools that automate tedious tasks without complexity or vendor lock-in.

**Core principles:**
- **Local-first** - Everything runs on your Mac, no cloud dependencies
- **Simple over clever** - Straightforward solutions that work reliably
- **User control** - You choose when and how tools run
- **No magic** - Plain scripts you can read, modify, and understand

**What belongs here:**
- Tools that save significant time on repetitive tasks
- Automation that enhances existing workflows (email, git, browser)
- Scripts that integrate local services (LLMs, Mail.app, Chrome)

**What doesn't:**
- Complex frameworks requiring extensive configuration
- Cloud-dependent services
- Tools duplicating existing solutions without clear advantage

## Tools

### ExtensionAuditor (🟢 5 minutes)
Chrome extension security scanner. Analyzes installed extensions and generates CRXplorer-compatible reports.

**Use case:** Audit browser extensions for security risks, outdated versions, and malicious code.

**Get started:** Zero dependencies - just run it:
```bash
python3 ExtensionAuditor/extension-auditor.py
```
[Full documentation →](./ExtensionAuditor/)

---

### SegmentSalmon (🟢 5 minutes)
M3U8/HLS video stream downloader. Downloads video segments in parallel with lossless quality preservation.

**Use case:** Download streaming videos from M3U8 playlists (HLS streams) with concurrent downloads and smart retry logic.

**Get started:** Automatic dependency management - just run it:
```bash
SegmentSalmon/segment-salmon 'https://example.com/playlist.m3u8'
```
[Full documentation →](./SegmentSalmon/)

---

### SwiftHAL (🟢 5 minutes)
Swift CLI tool for Halstead complexity metrics. Analyzes code complexity with visual TUI and architecture insights.

**Use case:** Track code complexity, prioritize refactoring, identify hotspots, enforce quality gates in CI/CD.

**Get started:** Build from source or download binary release:
```bash
cd SwiftHAL && swift build -c release
cp .build/release/SwiftHAL /usr/local/bin/hal
hal --path Sources
```
[Full documentation →](./SwiftHAL/)

---

### CommitCraft (🟡 10 minutes)
Development workflow toolkit for Claude Code. AI-generated conventional commits, GitHub issue validation, PR creation, and release guidance across 6 workflows.

**Use case:** Automate commits, PRs, and releases with security checks, conventional format, issue tracking, and AI-generated descriptions.

**Get started:** One-time global install, works in all repositories:
```bash
cd CommitCraft && ./commitcraft-install.sh
```
[Full documentation →](./CommitCraft/)

---

### Summarizer (🔴 30 minutes)
Automated Google Alert intelligence digest generator. Monitors Mail.app, fetches articles, summarizes with local LLM.

**Use case:** Stay informed on industry trends, competitor news, research papers without reading every article.

**Get started:** Requires LM Studio, Mail.app, and SMTP configuration:

[Complete setup guide →](./docs/SETUP.md)

## Quick Start

**Choose a tool to try first:**

### 🟢 ExtensionAuditor (Easiest)

No setup required. Instant results.

```bash
cd ~/Code
git clone https://github.com/starfysh-tech/AppletScriptorium.git
cd AppletScriptorium

# Run it
python3 ExtensionAuditor/extension-auditor.py
```

**Output:** `extensions.csv` with all your Chrome extensions analyzed and ready for security review.

**Next:** Upload to [CRXplorer](https://crxplorer.com/) for detailed vulnerability scanning.

---

### 🟡 CommitCraft (Best for Developers)

One-time install, works everywhere.

```bash
# After cloning (above)
cd CommitCraft
./commitcraft-install.sh

# Use in any git repository
cd ~/your-project
/commitcraft push      # AI-generated commit + push with issue tracking
/commitcraft release   # Semantic version guidance and release workflow
```

**Next:** Read [CommitCraft/README.md](./CommitCraft/) for full command documentation.

---

### 🔴 Summarizer (Most Powerful)

Requires LM Studio + Mail.app + SMTP setup.

**Setup:** Follow complete guide at [docs/SETUP.md](./docs/SETUP.md)

**Time:** 30 minutes for first-time setup

**Reward:** Automated intelligence digests delivered to your inbox

---

## Repository Structure

```
.
├── .env.template                 # Environment variable template (copy to .env)
├── AGENTS.md                     # AI assistant guidelines (Codex, Gemini, etc.)
├── CLAUDE.md                     # Claude Code development guide
├── docs/                         # Documentation
│   ├── SETUP.md                  # Installation guide
│   ├── TROUBLESHOOTING.md        # Common issues and solutions
│   ├── workflow-diagram.png      # Visual workflow diagram
│   └── workflow-diagram.mmd      # Mermaid source for diagram
├── Summarizer/                   # Google Alert Intelligence tool
│   ├── config.py                 # Configuration constants
│   ├── cli.py                    # Main orchestrator
│   ├── link_extractor.py         # Extract links from alert emails
│   ├── article_fetcher.py        # HTTP fetcher with Markdown fallbacks (url-to-md / Jina)
│   ├── urltomd_fetcher.py        # url-to-md CLI wrapper for Markdown fallbacks
│   ├── jina_fetcher.py           # Jina Reader API fallback
│   ├── markdown_cleanup.py       # Markdown content cleaning and validation
│   ├── content_cleaner.py        # HTML to Markdown conversion
│   ├── summarizer.py             # LLM summarization
│   ├── digest_renderer.py        # HTML/text digest generation
│   ├── fetch-alert-source.applescript  # Manual alert capture
│   ├── templates/process-alert.scpt    # Mail rule automation
│   ├── requirements.txt          # Python dependencies
│   ├── Samples/                  # Fixtures for regression tests
│   └── tests/                    # Pytest suite
├── ExtensionAuditor/             # Chrome extension security scanner
│   ├── extension-auditor.py      # Main scanner script (cross-platform)
│   └── README.md                 # Usage documentation
├── SegmentSalmon/                # M3U8/HLS video stream downloader
│   ├── segment-salmon            # Shell wrapper with dependency management
│   ├── m3u8_downloader.py        # Main downloader script
│   └── README.md                 # Usage documentation
├── SwiftHAL/                     # Halstead complexity metrics analyzer
│   ├── Sources/                  # Swift source code
│   ├── Tests/                    # Test suite
│   ├── Package.swift             # Swift package manifest
│   └── README.md                 # Usage documentation
├── CommitCraft/                  # Development workflow toolkit (Claude Code skill)
│   ├── SKILL.md                  # Skill definition — routes /commitcraft <arg>
│   ├── commitcraft-install.sh    # Global installer with TUI
│   ├── commitcraft-setup.sh      # Interactive tooling setup + --check mode
│   ├── commitcraft-issues.sh     # Branch-based GitHub issue validation
│   ├── commitcraft-release-analyze.sh  # Semantic version analysis
│   ├── workflows/                # 6 workflow files (commit, push, pr, release, setup, check)
│   ├── templates/                # 7 config templates (commitlint, gitleaks, pre-commit, CI)
│   └── README.md                 # Setup and usage guide
└── README.md                     # This file
```

Future tools will live alongside existing tools. Shared utilities will migrate to `shared/` when needed.


---

## Testing

Each tool includes tests or validation:

```bash
# Summarizer - Full test suite
python3 -m pytest Summarizer/tests

# ExtensionAuditor - Dry run validation
python3 ExtensionAuditor/extension-auditor.py --help

# SegmentSalmon - Help and validation
SegmentSalmon/segment-salmon --help

# CommitCraft - Validate tooling configuration
~/.claude/skills/commitcraft/commitcraft-setup.sh --check
```

---

## Development

**AI Assistant Guides:**
- **Claude Code**: [CLAUDE.md](./CLAUDE.md) - Development commands, code style, module patterns
- **Other AI**: [AGENTS.md](./AGENTS.md) - Build commands, project conventions

**Configuration:**
- Create `.env` from [.env.template](./.env.template)
- Tool-specific configs in `Tool/config.py` or `Tool/README.md`

**Key Conventions:**
- Python module invocation: `python3 -m Tool.cli` (not direct script paths)
- System Python required (Summarizer Mail rules)
- Snake_case for functions/variables
- Conventional Commits for git messages

---

## Contributing New Tools

New tools should follow these guidelines:

1. **Solve a real problem** - Automate something genuinely tedious
2. **Keep it simple** - Straightforward implementation over clever abstraction
3. **Work locally** - Prefer local execution, avoid cloud dependencies
4. **Document clearly** - README with usage examples and troubleshooting
5. **Test thoroughly** - Include test suite or validation script

**Directory structure:**
```
ToolName/
├── main-script.py           # Primary script
├── config.py                # Configuration (if needed)
├── README.md                # Usage documentation
├── requirements.txt         # Dependencies (if Python)
└── tests/                   # Test suite
```

**Before contributing:**
- Check existing tools don't already solve this
- Verify it runs reliably on macOS
- Include setup/installation instructions
- Add troubleshooting section

See individual tool READMEs for examples.

---

## Philosophy

These tools embody Larry Wall's three great virtues of a programmer:

### Laziness
**"The quality that makes you go to great effort to reduce overall energy expenditure."**

Automate tedious tasks so you never do them manually again:
- **Summarizer:** Never read 20 articles when AI can distill the key insights for you
- **ExtensionAuditor:** Security audit in one command, not hours of manual clicking and research
- **CommitCraft:** Beautiful commit messages and releases without thinking about format or versioning

### Impatience
**"The anger you feel when the computer is being lazy."**

Get results immediately, no complex setup or waiting:
- **ExtensionAuditor:** Zero configuration, instant CSV output
- **CommitCraft:** One install command, works in every repository forever
- **Summarizer:** Configure once, then automated intelligence digests arrive like clockwork

### Hubris
**"The quality that makes you write programs that other people won't want to say bad things about."**

Build tools good enough that others want to use them:
- **Local-first:** No cloud dependencies or vendor lock-in
- **Transparent:** Plain scripts anyone can read, modify, and understand
- **Respectful:** Documentation that values your time, minimal configuration, clear error messages

> "We will encourage you to develop the three great virtues of a programmer: laziness, impatience, and hubris."
> — Larry Wall, *Programming Perl* (1991)

---

## Support

- **Setup issues**: [SETUP.md](./docs/SETUP.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)
- **Development**: [CLAUDE.md](./CLAUDE.md) or [AGENTS.md](./AGENTS.md)
- **Logs**: `runs/*/workflow.log`
