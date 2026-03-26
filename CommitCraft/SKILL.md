---
name: commitcraft
description: AI-powered conventional commits, issue validation, PR creation, and release guidance
argument-hint: [commit|push|pr|release|setup|check]
allowed-tools: [Bash, Read, Write, Edit, ToolSearch, AskUserQuestion]
context: fork
model: haiku
---

# CommitCraft

**MANDATORY FIRST STEP — DO NOT SKIP:**
You MUST call `ToolSearch` with query `select:AskUserQuestion` RIGHT NOW before reading any workflow file or doing anything else. AskUserQuestion is a deferred tool that will not exist until you load it. If you skip this step, you will be unable to ask the user questions interactively and will have to fall back to plain text.

1. Call `ToolSearch` with query `select:AskUserQuestion` — wait for it to return before continuing
2. Confirm AskUserQuestion is now available (it will appear in the results)
3. Proceed with the workflow

## Execution Policy

**Every git command runs in the foreground. One attempt per phase. No retries, no background tasks, no `--no-verify`.** Pre-commit hooks can take 60-90 seconds — wait for them.

Read `~/.claude/skills/commitcraft/workflows/$ARGUMENTS.md` and follow its instructions exactly. If the file does not exist or cannot be read, read `~/.claude/skills/commitcraft/workflows/commit.md` instead. Do not skip steps.

Working directory: `$WORKING_DIRECTORY`
