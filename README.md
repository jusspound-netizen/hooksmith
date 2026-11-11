# Hooksmith

**Write agent guardrails once. Compile to native hooks for Claude Code, Cursor, and Codex.**

The hook schemas are incompatible. A `PreToolUse` hook that works in Claude Code will not work in Cursor or Codex without translation. Hooksmith is the compiler that does that translation for you.

---

## The problem

| Field | Claude Code | Cursor | Codex |
|---|---|---|---|
| Config file | `.claude/settings.json` | `.cursor/hooks.json` | `.codex/hooks.json` |
| Event name | `PreToolUse` | `preToolUse` | `PreToolUse` |
| Block mechanism | `permissionDecision: deny` | `permission: deny` | `permissionDecision: deny` |
| Ask support | supported | supported | **not supported** |
| Tool input | stdin JSON | stdin JSON | stdin JSON |

You should not have to write three different hook configurations to enforce one policy.

## The solution

Write the policy once, in YAML:

```yaml
policies:
  - name: block-destructive-shell
    match: Bash
    block_if: command =~ /rm\\s+-rf|git\\s+reset\\s+--hard/
    decision: deny
    reason: "Destructive command blocked by hooksmith"
```

Compile it to every harness:

```bash
python scripts/compile.py --project /path/to/project --harness all
```

Hooksmith writes the correct native config for each one, and generates a self-contained guard script per policy in `.hooksmith/`.

---

## What it handles for you

| Concern | How Hooksmith handles it |
|---|---|
| **Schema translation** | The same policy compiles to the correct native format for each harness. |
| **Ask downgrade** | `decision: ask` becomes `deny` on Codex, because Codex has no `ask` for `PreToolUse`. |
| **Input format** | Guard scripts read `tool_input` from stdin as JSON, the documented Claude Code 2.x format. |
| **Backups** | Every config file is backed up to `<file>.bak` before overwrite. |
| **Self-contained guards** | Each policy becomes a small Python script in `.hooksmith/`. No runtime bridge, no dependencies. |

## Verification status

| Claim | Status |
|---|---|
| Compiles YAML to Claude Code hook config | ✅ tested |
| Generates guard scripts with correct regex | ✅ tested |
| Guard blocks destructive command (exit 2) | ✅ tested |
| Guard allows safe command (exit 0) | ✅ tested |
| Reads stdin in documented Claude Code format | ✅ tested |
| Works in a live Claude Code session | ⏳ not yet verified |
| Cursor and Codex schema output | ⏳ written, not tested against a live harness |

Hooksmith is honest about what is proven and what is not. The guard logic is verified against piped test payloads. The schema translation is written against the documented formats. The one thing that has not been tested is a live run inside each harness.

## What it does not do

- **No runtime bridge.** The hooks are self-contained Python scripts. There is no daemon, no background process, no network call.
- **No network calls.** The compiler reads a YAML file and writes JSON. Nothing leaves the machine.
- **No dependencies beyond Python 3.9+ and stdlib.** No `pip install` required.

## Installation

```bash
git clone https://github.com/jusspound-netizen/hooksmith.git
cd hooksmith
```

No install step. Run the compiler directly.

## License

MIT
