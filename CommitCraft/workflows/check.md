# Check Workflow

Validate current configuration:

```bash
~/.claude/skills/commitcraft/commitcraft-setup.sh --check
```

The script outputs a human-friendly report followed by a machine-parseable block between `COMMITCRAFT_CHECK_START` and `COMMITCRAFT_CHECK_END`.

Display the results to the user. If critical components are missing (commitlint, gitleaks, precommit_hooks), add:

```
⚠ Tooling incomplete — run /commitcraft setup for full configuration
```

**Do NOT block commits** — repos without tooling still get AI-generated commit messages.
