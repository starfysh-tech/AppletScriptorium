# Setup Workflow

Run the interactive setup script.

**Note:** To run a specific section like signing, use the script directly:
```bash
~/.claude/skills/commitcraft/commitcraft-setup.sh --section signing
```

Or run the full interactive setup:

```bash
~/.claude/skills/commitcraft/commitcraft-setup.sh
```

The skill does not currently support passing `--section` arguments through `/commitcraft setup` due to how `$ARGUMENTS` is parsed. The user should run the script directly via Bash for section-specific setup.
