#!/usr/bin/env python3
"""Measure the fixed context overhead an AI coding agent pays on every turn.

Counts always-on instructions (AGENTS.md, CLAUDE.md and its imports,
alwaysApply Cursor rules, legacy .cursorrules), the description-only cost of
on-demand rules and skills, and MCP tool definitions when they are recorded
in .railguards/mcp-lock.json.

Usage:
  measure_overhead.py [ROOT] [--json] [--save-baseline] [--compare]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BASELINE_PATH = Path(".railguards") / "overhead-baseline.json"
LOCK_PATH = Path(".railguards") / "mcp-lock.json"
SKILL_DIRS = (".agents/skills", ".cursor/skills", ".claude/skills")
MCP_CONFIGS = {
    ".cursor/mcp.json": ("cursor",),
    ".mcp.json": ("claude", "cursor"),
}
IMPORT_RE = re.compile(r"^@(\S+)\s*$", re.MULTILINE)

try:
    import tiktoken  # type: ignore

    _ENCODER = tiktoken.get_encoding("o200k_base")
    TOKENIZER = "tiktoken:o200k_base"
except Exception:  # noqa: BLE001 - optional dependency
    _ENCODER = None
    TOKENIZER = "chars/4"


def estimate_tokens(text: str) -> int:
    if _ENCODER is not None:
        return len(_ENCODER.encode(text))
    return (len(text) + 3) // 4


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def parse_frontmatter(text: str) -> dict:
    """Minimal YAML frontmatter parser for flat `key: value` pairs."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, _, value = line.partition(":")
            data[key.strip()] = value.strip().strip("\"'")
    return data


def _entry(root: Path, path: Path, tools: list[str], text: str | None = None) -> dict:
    text = _read(path) if text is None else text
    return {
        "path": path.relative_to(root).as_posix(),
        "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
        "tokens": estimate_tokens(text),
        "tools": tools,
    }


def _claude_files(root: Path) -> list[Path]:
    """CLAUDE.md files plus their @imports, each file once."""
    seen: list[Path] = []
    queue = [p for p in (root / "CLAUDE.md", root / ".claude" / "CLAUDE.md") if p.is_file()]
    while queue:
        path = queue.pop(0).resolve()
        if path in seen or not path.is_file():
            continue
        try:
            path.relative_to(root.resolve())
        except ValueError:
            continue
        seen.append(path)
        for match in IMPORT_RE.finditer(_read(path)):
            target = match.group(1)
            if target.startswith("~"):
                continue
            queue.append((path.parent / target))
    return seen


def measure(root: Path) -> dict:
    root = Path(root).resolve()
    always: dict[str, dict] = {}

    def add(path: Path, tool: str) -> None:
        key = path.resolve().relative_to(root).as_posix()
        if key in always:
            if tool not in always[key]["tools"]:
                always[key]["tools"].append(tool)
        else:
            always[key] = _entry(root, path.resolve(), [tool])

    agents = root / "AGENTS.md"
    if agents.is_file():
        add(agents, "cursor")
    legacy = root / ".cursorrules"
    if legacy.is_file():
        add(legacy, "cursor")

    on_demand: list[dict] = []
    rules_dir = root / ".cursor" / "rules"
    if rules_dir.is_dir():
        for rule in sorted(rules_dir.rglob("*")):
            if rule.suffix not in (".mdc", ".md") or not rule.is_file():
                continue
            meta = parse_frontmatter(_read(rule))
            if meta.get("alwaysApply", "").lower() == "true":
                add(rule, "cursor")
            else:
                desc = meta.get("description", "")
                on_demand.append(
                    {"path": rule.relative_to(root).as_posix(), "tokens": estimate_tokens(desc), "tools": ["cursor"]}
                )

    for path in _claude_files(root):
        add(path, "claude")

    for skill_dir in SKILL_DIRS:
        base = root / skill_dir
        if not base.is_dir():
            continue
        tools = ["claude", "cursor"] if skill_dir.startswith(".claude") else ["cursor"]
        for skill in sorted(base.glob("*/SKILL.md")):
            meta = parse_frontmatter(_read(skill))
            text = f"{meta.get('name', '')}: {meta.get('description', '')}"
            on_demand.append({"path": skill.relative_to(root).as_posix(), "tokens": estimate_tokens(text), "tools": tools})

    lock_tools = {}
    lock_file = root / LOCK_PATH
    if lock_file.is_file():
        try:
            lock = json.loads(_read(lock_file))
            for name, server in lock.get("servers", {}).items():
                if server.get("tools") is not None:
                    lock_tools[name] = estimate_tokens(json.dumps(server["tools"], sort_keys=True))
        except json.JSONDecodeError:
            pass

    servers: list[dict] = []
    for rel, tools in MCP_CONFIGS.items():
        config = root / rel
        if not config.is_file():
            continue
        try:
            data = json.loads(_read(config))
        except json.JSONDecodeError:
            continue
        for name in sorted((data.get("mcpServers") or {}).keys()):
            servers.append({"name": name, "source": rel, "tool_tokens": lock_tools.get(name), "tools": list(tools)})

    per_tool = {"cursor": 0, "claude": 0}
    for entry in always.values():
        for tool in entry["tools"]:
            per_tool[tool] += entry["tokens"]
    for entry in on_demand:
        for tool in entry["tools"]:
            per_tool[tool] += entry["tokens"]
    for server in servers:
        for tool in server["tools"]:
            per_tool[tool] += server["tool_tokens"] or 0

    return {
        "root": str(root),
        "tokenizer": TOKENIZER,
        "always_on": sorted(always.values(), key=lambda e: e["path"]),
        "on_demand": on_demand,
        "mcp_servers": servers,
        "per_tool": per_tool,
        "total_tokens": max(per_tool.values()),
    }


def save_baseline(root: Path, result: dict) -> Path:
    path = Path(root) / BASELINE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return path


def compare(root: Path, current: dict) -> dict:
    path = Path(root) / BASELINE_PATH
    if not path.is_file():
        raise FileNotFoundError(f"No baseline at {path}; run with --save-baseline first.")
    before = json.loads(path.read_text(encoding="utf-8"))
    per_tool = {}
    for tool in current["per_tool"]:
        old = before.get("per_tool", {}).get(tool, 0)
        new = current["per_tool"][tool]
        per_tool[tool] = {"before": old, "after": new, "delta": new - old}
    old_paths = {e["path"] for e in before.get("always_on", [])}
    new_paths = {e["path"] for e in current["always_on"]}
    old_servers = {s["name"] for s in before.get("mcp_servers", [])}
    new_servers = {s["name"] for s in current["mcp_servers"]}
    return {
        "per_tool": per_tool,
        "removed_always_on": sorted(old_paths - new_paths),
        "added_always_on": sorted(new_paths - old_paths),
        "removed_mcp_servers": sorted(old_servers - new_servers),
        "added_mcp_servers": sorted(new_servers - old_servers),
    }


def render(result: dict) -> str:
    lines = [f"Fixed context overhead ({result['tokenizer']})", ""]
    lines.append("Always-on instructions:")
    for e in result["always_on"]:
        lines.append(f"  {e['tokens']:>7} tokens  {e['lines']:>5} lines  {e['path']}  [{', '.join(e['tools'])}]")
    if not result["always_on"]:
        lines.append("  (none)")
    lines.append("On-demand rules and skills (description only):")
    for e in result["on_demand"]:
        lines.append(f"  {e['tokens']:>7} tokens  {e['path']}")
    if not result["on_demand"]:
        lines.append("  (none)")
    lines.append("MCP servers:")
    for s in result["mcp_servers"]:
        tokens = "unknown" if s["tool_tokens"] is None else f"{s['tool_tokens']} tokens"
        lines.append(f"  {s['name']:<20} {tokens:<16} {s['source']}")
    if not result["mcp_servers"]:
        lines.append("  (none)")
    if any(s["tool_tokens"] is None for s in result["mcp_servers"]):
        lines.append("  Tool-definition tokens are unknown until recorded with: scripts/mcp_lock.py snapshot --probe")
    lines.append("")
    for tool, total in result["per_tool"].items():
        lines.append(f"Per-turn total for {tool}: {total} tokens")
    return "\n".join(lines)


def render_compare(diff: dict) -> str:
    lines = ["Fixed overhead, before vs after:"]
    for tool, row in diff["per_tool"].items():
        sign = "+" if row["delta"] > 0 else ""
        lines.append(f"  {tool:<7} {row['before']:>7} -> {row['after']:>7}  ({sign}{row['delta']})")
    for key in ("removed_always_on", "added_always_on", "removed_mcp_servers", "added_mcp_servers"):
        if diff[key]:
            lines.append(f"  {key.replace('_', ' ')}: {', '.join(diff[key])}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--save-baseline", action="store_true", help=f"write {BASELINE_PATH}")
    parser.add_argument("--compare", action="store_true", help="compare against the saved baseline")
    args = parser.parse_args(argv)

    root = Path(args.root)
    result = measure(root)
    if args.compare:
        try:
            diff = compare(root, result)
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(json.dumps(diff, indent=2) if args.json else render_compare(diff))
        return 0
    if args.save_baseline:
        path = save_baseline(root, result)
        print(f"Baseline saved to {path}", file=sys.stderr)
    print(json.dumps(result, indent=2) if args.json else render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
