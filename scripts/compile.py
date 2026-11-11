#!/usr/bin/env python3
"""Hooksmith - compile YAML policies to native agent hook configs."""
import argparse, json, re, shutil, sys
from pathlib import Path

# Schema translation table: the technical moat
HARNESSES = {
    "claude": {
        "config": ".claude/settings.json",
        "event": "PreToolUse",
        "block_key": "permissionDecision",
        "block_value": "deny",
        "ask_supported": True,
    },
    "cursor": {
        "config": ".cursor/hooks.json",
        "event": "preToolUse",
        "block_key": "permission",
        "block_value": "deny",
        "ask_supported": True,
    },
    "codex": {
        "config": ".codex/hooks.json",
        "event": "PreToolUse",
        "block_key": "permissionDecision",
        "block_value": "deny",
        "ask_supported": False,  # Codex cannot "ask" on PreToolUse
    },
}

def parse_policies(yaml_path):
    policies = []
    current = None
    for line in yaml_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.strip().startswith("- name:"):
            if current:
                policies.append(current)
            current = {"name": line.split(":", 1)[1].strip()}
        elif current is not None and ":" in line and not line.lstrip().startswith("-"):
            key, val = line.strip().split(":", 1)
            current[key.strip()] = val.strip().strip(chr(34)).strip(chr(39))
    if current:
        policies.append(current)
    return policies

def make_hook_command(policy, harness):
    match = policy.get("match", "*")
    condition = policy.get("block_if", "")
    reason = policy.get("reason", "Blocked by hooksmith")
    decision = policy.get("decision", "deny")
    if decision == "ask" and not HARNESSES[harness]["ask_supported"]:
        decision = "deny"
        reason += " (ask downgraded to deny on Codex)"
    # Reference a guard script the compiler writes alongside the config
    guard_name = policy.get("name", "guard").replace(" ", "-") + ".py"
    return f"python .hooksmith/{guard_name}"

def write_guard_scripts(policies, project):
    gdir = project / ".hooksmith"
    gdir.mkdir(exist_ok=True)
    for p in policies:
        name = p.get("name", "guard").replace(" ", "-")
        condition = p.get("block_if", "")
        reason = p.get("reason", "Blocked by hooksmith")
        # Extract the regex from "field =~ /pattern/"
        m = re.search(r'=~\s*/(.+?)/', condition)
        regex = m.group(1) if m else ""
        # Extract the field name from "field =~ ..." or "field not in ..."
        fld = re.search(r'^(\w+)', condition)
        field_name = fld.group(1) if fld else "command"
        body = (
            f'#!/usr/bin/env python3\n'
            f'"""Hooksmith guard: {name}"""\n'
            f'import sys, json, re\n'
            f'\n'
            f'try:\n'
            f'    data = json.load(sys.stdin)\n'
            f'except Exception:\n'
            f'    sys.exit(0)\n'
            f'\n'
            f'value = str(data.get("tool_input", {{}}).get("{field_name}", ""))\n'
            f'if re.search(r"""{regex}""", value):\n'
            f'    print("{reason}", file=sys.stderr)\n'
            f'    sys.exit(2)\n'
            f'sys.exit(0)\n'
        )
        (gdir / (name + ".py")).write_text(body, encoding="utf-8")
    print(f"Wrote {len(policies)} guard scripts to {gdir}")
def compile_for_harness(policies, harness, project):
    cfg = HARNESSES[harness]
    cfg_path = project / cfg["config"]
    hooks = []
    for p in policies:
        hooks.append({
            "matcher": p.get("match", "*"),
            "hooks": [{"type": "command", "command": make_hook_command(p, harness)}]
        })
    if cfg_path.exists():
        data = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
        shutil.copy(cfg_path, cfg_path.with_suffix(cfg_path.suffix + ".bak"))
    else:
        data = {}
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
    data.setdefault("hooks", {})[cfg["event"]] = hooks
    cfg_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {len(hooks)} hooks to {cfg_path}")
    if cfg_path.with_suffix(cfg_path.suffix + ".bak").exists():
        print(f"  Backup: {cfg_path}.bak")

def main():
    ap = argparse.ArgumentParser(description="Compile hooksmith.yaml to native hook configs")
    ap.add_argument("--project", default=".", help="Project root")
    ap.add_argument("--harness", choices=["claude", "cursor", "codex", "all"], default="all")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    project = Path(args.project).resolve()
    yaml_path = project / "hooksmith.yaml"
    if not yaml_path.exists():
        print(f"ERROR: hooksmith.yaml not found in {project}")
        return 2
    policies = parse_policies(yaml_path)
    if not args.dry_run:
        write_guard_scripts(policies, project)
    if not policies:
        print("ERROR: no policies found in hooksmith.yaml")
        return 2
    print(f"Loaded {len(policies)} policies")
    targets = ["claude", "cursor", "codex"] if args.harness == "all" else [args.harness]
    for h in targets:
        if args.dry_run:
            print(f"\\n--- {h} (dry run) ---")
            print(json.dumps({"hooks": {HARNESSES[h]["event"]: [
                {"matcher": p.get("match", "*"), "command": make_hook_command(p, h)}
                for p in policies
            ]}}, indent=2))
        else:
            compile_for_harness(policies, h, project)
    return 0

if __name__ == "__main__":
    sys.exit(main())
