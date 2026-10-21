#!/usr/bin/env python3
"""Install RAILGUARDS into a project for Cursor, Claude Code, or both.

  install.sh [TARGET] [--tool auto|cursor|claude|both] [--core agents-md|cursor-rule]
             [--profile ask|strict] [--no-hooks] [--uninstall]

Never overwrites user content: Markdown and .gitignore changes live between
RAILGUARDS markers, JSON hook configs are merged, and re-running is idempotent.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
BEGIN, END = "<!-- RAILGUARDS:BEGIN -->", "<!-- RAILGUARDS:END -->"
GITIGNORE_BEGIN, GITIGNORE_END = "# RAILGUARDS:BEGIN", "# RAILGUARDS:END"
GUARD_MARKER = ".railguards/hooks/guard.py"
ENGINE_SCRIPTS = ("check_unicode.py", "measure_overhead.py", "mcp_lock.py")
SKILL_DIRS = (".agents/skills", ".claude/skills", ".cursor/skills")
GITIGNORE_LINES = (".railguards/audit-log.jsonl", ".railguards/progress.md")
CURSOR_PERMISSION_EVENTS = ("beforeShellExecution", "beforeReadFile")
V1_RULE_FILES = frozenset(f"{name}.mdc" for name in (
    "00-railguard-core", "01-security-analysis-trigger", "02-input-validation", "03-authentication",
    "04-llm-prompt-injection", "05-sql-injection-prevention", "06-xss-prevention", "07-logic-vulnerability-analysis",
    "08-cors-severity-assessment", "12-xss-ssti-detection", "13-output-format-rules", "14-security-analysis-workflow",
    "15-standardized-finding-format", "16-validation-and-quality-assurance", "17-severity-assessment-framework",
    "18-code-analysis-focus-areas", "19-language-detection-and-matching", "20-specialized-rule-dispatch",
    "21-xss-type-classification", "23-hardcoded-credentials-detection", "24-registration-auth-context-analysis",
    "25-deserialization-detection", "26-serialization-usage-discovery", "27-cors-usage-discovery",
    "28-false-positive-and-mitigation-analysis", "exclusions",
))
ALLOW_READ_HEADER = (
    "# Paths (gitignore-style globs, relative to the project root) that RAILGUARDS lets agents read\n"
    "# even though they look like secret files. One per line. Example: config/.env.test\n"
)


class InstallError(Exception):
    pass


def upsert_block(text: str, block: str, begin: str = BEGIN, end: str = END) -> str:
    """Insert or replace the marked block; content outside the markers is untouched."""
    block = block.strip("\n")
    start = text.find(begin)
    if start != -1:
        stop = text.find(end, start)
        if stop == -1:
            raise InstallError(f"found {begin} without a matching {end}; fix the file and re-run")
        return text[:start] + block + text[stop + len(end):]
    if not text.strip():
        return block + "\n"
    return text.rstrip("\n") + "\n\n" + block + "\n"


def remove_block(text: str, begin: str = BEGIN, end: str = END) -> str:
    start = text.find(begin)
    if start == -1:
        return text
    stop = text.find(end, start)
    if stop == -1:
        raise InstallError(f"found {begin} without a matching {end}; fix the file and re-run")
    before, after = text[:start].rstrip("\n"), text[stop + len(end):].lstrip("\n")
    if before and after:
        return before + "\n\n" + after
    return (before or after).rstrip("\n") + "\n" if (before or after) else ""


def _is_ours(command: str) -> bool:
    return GUARD_MARKER in (command or "")


def merge_cursor_hooks(existing: dict, ours: dict) -> dict:
    """Drop previous RAILGUARDS entries, keep everything else, then add ours."""
    merged = dict(existing)
    merged.setdefault("version", ours.get("version", 1))
    hooks = {event: [h for h in entries if not _is_ours(h.get("command", ""))] for event, entries in (existing.get("hooks") or {}).items()}
    for event, entries in ours.get("hooks", {}).items():
        hooks.setdefault(event, []).extend(entries)
    merged["hooks"] = {event: entries for event, entries in hooks.items() if entries}
    return merged


def strip_cursor_hooks(existing: dict) -> dict:
    return merge_cursor_hooks(existing, {"hooks": {}})


def merge_claude_settings(existing: dict, ours: dict) -> dict:
    merged = dict(existing)
    hooks = {}
    for event, groups in (existing.get("hooks") or {}).items():
        kept = []
        for group in groups:
            inner = [h for h in group.get("hooks", []) if not _is_ours(h.get("command", ""))]
            if inner:
                kept.append({**group, "hooks": inner})
        hooks[event] = kept
    for event, groups in ours.get("hooks", {}).items():
        hooks.setdefault(event, []).extend(groups)
    hooks = {event: groups for event, groups in hooks.items() if groups}
    if hooks:
        merged["hooks"] = hooks
    else:
        merged.pop("hooks", None)
    return merged


def strip_claude_settings(existing: dict) -> dict:
    return merge_claude_settings(existing, {"hooks": {}})


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise InstallError(f"{path} is not valid JSON ({exc}); fix it and re-run") from exc
    if not isinstance(data, dict):
        raise InstallError(f"{path} must contain a JSON object")
    return data


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _edit_text(path: Path, transform) -> None:
    old = path.read_text(encoding="utf-8") if path.is_file() else ""
    new = transform(old)
    if new == old:
        return
    if new.strip():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
    elif path.exists():
        path.unlink()


def core_block() -> str:
    text = (SRC / "AGENTS.md").read_text(encoding="utf-8")
    start, stop = text.index(BEGIN), text.index(END) + len(END)
    return text[start:stop]


def detect_tools(target: Path) -> set[str]:
    tools = set()
    if (target / ".cursor").is_dir() or (target / ".cursorrules").exists():
        tools.add("cursor")
    if (target / ".claude").is_dir() or (target / "CLAUDE.md").exists():
        tools.add("claude")
    return tools or {"cursor"}


def resolve_tools(choice: str, target: Path) -> set[str]:
    return {"cursor", "claude"} if choice == "both" else detect_tools(target) if choice == "auto" else {choice}


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def _remove_skills(target: Path, skill_dir: str) -> None:
    base = target / skill_dir
    for path in base.glob("railguards-*") if base.is_dir() else []:
        shutil.rmtree(path)


def install(target: Path, tools: set[str], core: str = "agents-md", profile: str = "ask", hooks: bool = True) -> list[str]:
    target = Path(target).resolve()
    if not target.is_dir():
        raise InstallError(f"target directory does not exist: {target}")
    if target == SRC:
        raise InstallError("refusing to install RAILGUARDS into its own source repository")
    done: list[str] = []

    rg = target / ".railguards"
    (rg / "hooks").mkdir(parents=True, exist_ok=True)
    (rg / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC / "hooks" / "guard.py", rg / "hooks" / "guard.py")
    for name in ENGINE_SCRIPTS:
        shutil.copy2(SRC / "scripts" / name, rg / "scripts" / name)
    config = _read_json(rg / "config.json")
    config["profile"] = profile
    _write_json(rg / "config.json", config)
    if not (rg / "allow-read").exists():
        (rg / "allow-read").write_text(ALLOW_READ_HEADER, encoding="utf-8")
    done.append(f".railguards/ (hook engine, scripts, profile={profile})")

    if "claude" in tools and core == "cursor-rule":
        done.append("note: Claude Code needs AGENTS.md, so the core goes there instead of a Cursor rule")
        core = "agents-md"
    rule = target / ".cursor" / "rules" / "railguards.mdc"
    if core == "agents-md":
        _edit_text(target / "AGENTS.md", lambda t: upsert_block(t, core_block()))
        if rule.exists():
            rule.unlink()
        done.append("AGENTS.md (RAILGUARDS block)")
    else:
        rule.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SRC / "adapters" / "cursor" / "rules" / "railguards.mdc", rule)
        _edit_text(target / "AGENTS.md", remove_block)
        done.append(".cursor/rules/railguards.mdc")
    if "claude" in tools:
        claude_md = target / "CLAUDE.md"
        outside = remove_block(claude_md.read_text(encoding="utf-8")) if claude_md.is_file() else ""
        if "@AGENTS.md" in outside:
            done.append("CLAUDE.md already imports @AGENTS.md (unchanged)")
        else:
            block = (SRC / "adapters" / "claude-code" / "CLAUDE.md").read_text(encoding="utf-8")
            _edit_text(claude_md, lambda t: upsert_block(t, block))
            done.append("CLAUDE.md (@AGENTS.md import)")

    skill_dir = ".claude/skills" if "claude" in tools else ".agents/skills"
    for other in SKILL_DIRS:
        if other != skill_dir:
            _remove_skills(target, other)
    for skill in sorted((SRC / "skills").glob("railguards-*")):
        _copy_tree(skill, target / skill_dir / skill.name)
    done.append(f"{skill_dir}/railguards-* (skills)")

    for tool, adapter, agent_dir in (("cursor", "cursor", ".cursor/agents"), ("claude", "claude-code", ".claude/agents")):
        if tool not in tools:
            continue
        (target / agent_dir).mkdir(parents=True, exist_ok=True)
        for agent in sorted((SRC / "adapters" / adapter / "agents").glob("railguards-*.md")):
            shutil.copy2(agent, target / agent_dir / agent.name)
        done.append(f"{agent_dir}/railguards-*.md (subagents)")

    if hooks:
        if "cursor" in tools:
            ours = json.loads((SRC / "adapters" / "cursor" / "hooks.json").read_text(encoding="utf-8"))
            if profile == "strict":
                for event in CURSOR_PERMISSION_EVENTS:
                    for entry in ours["hooks"].get(event, []):
                        entry["failClosed"] = True
            path = target / ".cursor" / "hooks.json"
            _write_json(path, merge_cursor_hooks(_read_json(path), ours))
            done.append(".cursor/hooks.json (merged)")
        if "claude" in tools:
            ours = json.loads((SRC / "adapters" / "claude-code" / "settings.json").read_text(encoding="utf-8"))
            path = target / ".claude" / "settings.json"
            _write_json(path, merge_claude_settings(_read_json(path), ours))
            done.append(".claude/settings.json (merged)")

    _edit_text(target / ".gitignore", lambda t: upsert_block(t, "\n".join((GITIGNORE_BEGIN, *GITIGNORE_LINES, GITIGNORE_END)), GITIGNORE_BEGIN, GITIGNORE_END))
    done.append(".gitignore (RAILGUARDS block)")

    legacy = find_v1_rules(target)
    if legacy:
        done.append(f"warning: {len(legacy)} RAILGUARD v1 rule files still in .cursor/rules/ load on every request; remove them (see MIGRATION.md)")
    return done


def find_v1_rules(target: Path) -> list[Path]:
    rules = target / ".cursor" / "rules"
    if not rules.is_dir():
        return []
    return sorted(p for p in rules.glob("*.mdc") if p.name in V1_RULE_FILES)


def uninstall(target: Path) -> list[str]:
    target = Path(target).resolve()
    done: list[str] = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        _edit_text(target / name, remove_block)
    _edit_text(target / ".gitignore", lambda t: remove_block(t, GITIGNORE_BEGIN, GITIGNORE_END))
    done.append("removed RAILGUARDS blocks from AGENTS.md, CLAUDE.md, .gitignore")
    rule = target / ".cursor" / "rules" / "railguards.mdc"
    if rule.exists():
        rule.unlink()
    for skill_dir in SKILL_DIRS:
        _remove_skills(target, skill_dir)
    for agent_dir in (".cursor/agents", ".claude/agents"):
        for agent in (target / agent_dir).glob("railguards-*.md") if (target / agent_dir).is_dir() else []:
            agent.unlink()
    done.append("removed skills, subagents, and the Cursor rule")
    cursor_hooks = target / ".cursor" / "hooks.json"
    if cursor_hooks.is_file():
        _write_json(cursor_hooks, strip_cursor_hooks(_read_json(cursor_hooks)))
    claude_settings = target / ".claude" / "settings.json"
    if claude_settings.is_file():
        _write_json(claude_settings, strip_claude_settings(_read_json(claude_settings)))
    done.append("removed RAILGUARDS hooks (other hooks kept)")
    rg = target / ".railguards"
    for sub in ("hooks", "scripts"):
        if (rg / sub).is_dir():
            shutil.rmtree(rg / sub)
    if (rg / "config.json").exists():
        (rg / "config.json").unlink()
    if rg.is_dir() and not any(rg.iterdir()):
        rg.rmdir()
    elif rg.is_dir():
        kept = ", ".join(sorted(p.name for p in rg.iterdir()))
        done.append(f"kept your data in .railguards/ ({kept}); delete it manually if you no longer need it")
    return done


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", nargs="?", default=".", help="project directory (default: current directory)")
    parser.add_argument("--tool", choices=["auto", "cursor", "claude", "both"], default="auto")
    parser.add_argument("--core", choices=["agents-md", "cursor-rule"], default="agents-md", help="where the always-on layer goes (Claude Code always uses agents-md)")
    parser.add_argument("--profile", choices=["ask", "strict"], default="ask")
    parser.add_argument("--no-hooks", action="store_true", help="skip hook configuration")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args(argv)
    target = Path(args.target)
    try:
        if args.uninstall:
            for line in uninstall(target):
                print(f"- {line}")
            return 0
        tools = resolve_tools(args.tool, target)
        print(f"Installing RAILGUARDS for {', '.join(sorted(tools))} into {target.resolve()}")
        for line in install(target, tools, args.core, args.profile, not args.no_hooks):
            print(f"- {line}")
    except InstallError as exc:
        print(f"railguards install: {exc}", file=sys.stderr)
        return 1
    sys.path.insert(0, str(SRC / "scripts"))
    from measure_overhead import measure

    report = measure(target.resolve())
    overhead = ", ".join(f"{tool} {report['per_tool'][tool]}" for tool in sorted(tools))
    print(f"Fixed context overhead per request (estimated tokens): {overhead}. Details: python3 .railguards/scripts/measure_overhead.py")
    print("Next: restart your agent so it picks up the hooks, then try \"security audit\" or \"token plan\".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
