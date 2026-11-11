# Hooksmith

Write agent guardrails once. Compile them to native hooks for **Claude Code**, **Cursor**, and **Codex**.

The hook schemas are incompatible:

| Field | Claude Code | Cursor | Codex |
|---|---|---|---|
| Config | `.claude/settings.json` | `.cursor/hooks.json` | `.codex/hooks.json` |
| Event | `PreToolUse` | `preToolUse` | `PreToolUse` |
| Block | `permissionDecision: deny` | `permission: deny` | `permissionDecision: deny` |
| Ask | supported | supported | **not supported** |

Hooksmith handles the differences at compile time. Write a policy once, get native configs for every harness.

## Quick start

```bash
python scripts/compile.py --project /path/to/project
```

## The policy format

```yaml
policies:
  - name: block-destructive-shell
    match: Bash
    block_if: command =~ /rm\s+-rf|git\s+reset\s+--hard/
    decision: deny
    reason: "Destructive command blocked"
```

## What it handles for you

- **Schema translation**: the same policy compiles to the correct native format for each harness.
- **Ask downgrade**: `decision: ask` becomes `deny` on Codex, because Codex has no ask for `PreToolUse`.
- **Backups**: every config file is backed up before overwrite.

## What it does not do

- No runtime bridge. The hooks are self-contained Python one-liners.
- No network calls.
- No dependencies beyond Python 3.9+ and stdlib.

## License

MIT
