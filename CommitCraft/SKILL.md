---
name: commitcraft
description: AI-powered conventional commits, issue validation, PR creation, and release guidance
argument-hint: [commit|push|pr|release|setup|check]
allowed-tools: [Bash, Read, Write, Edit, AskUserQuestion]
context: fork
model: haiku
---

# CommitCraft

Read `~/.claude/skills/commitcraft/workflows/$ARGUMENTS.md` and follow its instructions exactly. If the file does not exist or cannot be read, read `~/.claude/skills/commitcraft/workflows/commit.md` instead. Do not skip steps.

Working directory: `$WORKING_DIRECTORY`
