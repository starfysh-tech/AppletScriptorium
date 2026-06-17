# CommitCraft has moved

CommitCraft is now distributed as a **Claude Code plugin** in the
[**nautilai**](https://github.com/starfysh-tech/nautilai) marketplace.

## Install

```text
/plugin marketplace add starfysh-tech/nautilai
/plugin install commitcraft@nautilai
```

## Use

```text
/commitcraft:commitcraft commit     # AI-generated conventional commit
/commitcraft:commitcraft push       # Commit + push with issue tracking
/commitcraft:commitcraft pr         # Create a PR with AI-generated description
/commitcraft:commitcraft release    # Semantic version bump and release guidance
/commitcraft:commitcraft setup      # Interactive tooling configuration
/commitcraft:commitcraft check      # Validate current configuration
```

It also triggers from natural language — "commit my changes", "open a PR",
"cut a release".

## Why the move

CommitCraft is tool-agnostic and useful in any repository, so it now lives in its own
marketplace alongside future Starfysh plugins rather than inside this project. The previous
`commitcraft-install.sh` global installer is superseded by Claude Code's native
`/plugin install`.

**Full docs:** https://github.com/starfysh-tech/nautilai/tree/main/commitcraft#readme
