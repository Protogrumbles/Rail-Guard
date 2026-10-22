#!/usr/bin/env python3
"""Repository consistency checks for RAILGUARDS (run in CI and before committing).

  ci_checks.py [--root DIR]

Checks: always-on budget, hidden Unicode, pillar completeness of detection
modules, adapter mirrors in sync, skill frontmatter, and valid JSON configs.
Exits 1 and lists every problem if any check fails.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_unicode import scan_text  # noqa: E402
from measure_overhead import estimate_tokens, parse_frontmatter  # noqa: E402

BEGIN, END = "<!-- RAILGUARDS:BEGIN -->", "<!-- RAILGUARDS:END -->"
MAX_LINES, MAX_TOKENS = 60, 1200
PILLARS = [
    "R: Risk First",
    "A: Attached Constraints",
    "I: Isolation",
    "L: Local Defaults",
    "G: Generative Path Checks",
    "U: Uncertainty Disclosure",
    "A: Auditability",
    "R: Review",
    "S: Spend",
]
PROCEDURE_MODULES = {"severity", "finding-format", "false-positive-filter"}
AUDITORS = {"web", "access", "secrets", "ai"}
EXTRA_RULE_PREFIXES = {"RG-XSS": ("RG-SSTI",)}
UNICODE_ALLOWLIST = ("evals/fixtures/poisoned-repo/",)
SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    return text[4:end], text[end + 5:]


def core_block_body(root: Path) -> str:
    text = _read(root / "AGENTS.md")
    start, stop = text.find(BEGIN), text.find(END)
    if start == -1 or stop == -1:
        raise ValueError("AGENTS.md is missing the RAILGUARDS markers")
    return text[start + len(BEGIN):stop].strip("\n") + "\n"


def check_budget(root: Path) -> list[str]:
    try:
        body = core_block_body(root)
    except ValueError as exc:
        return [str(exc)]
    errors = []
    lines = len(_read(root / "AGENTS.md").splitlines())
    if lines > MAX_LINES:
        errors.append(f"AGENTS.md has {lines} lines; the always-on budget is {MAX_LINES}")
    tokens = estimate_tokens(body)
    if tokens > MAX_TOKENS:
        errors.append(f"AGENTS.md RAILGUARDS block is about {tokens} tokens; the budget is {MAX_TOKENS}")
    return errors


def _repo_files(root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            capture_output=True, text=True, check=True,
        ).stdout
        return [root / rel for rel in out.split("\0") if rel]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts]


def check_unicode(root: Path) -> list[str]:
    errors = []
    for path in _repo_files(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(UNICODE_ALLOWLIST) or not path.is_file():
            continue
        try:
            text = _read(path)
        except (UnicodeDecodeError, OSError):
            continue
        for finding in scan_text(text)[:5]:
            errors.append(f"{rel}:{finding['line']}:{finding['col']}: hidden character {finding['codepoint']} {finding['name']}")
    for prefix in UNICODE_ALLOWLIST:
        planted = [p for p in (root / prefix).rglob("*") if p.is_file() and scan_text(_read(p))] if (root / prefix).is_dir() else []
        if (root / prefix).is_dir() and not planted:
            errors.append(f"{prefix} is allowlisted for hidden Unicode but no longer contains any (the eval fixture lost its payload)")
    return errors


def check_pillars(root: Path) -> list[str]:
    errors = []
    modules_dir = root / "skills" / "railguards-audit" / "modules"
    agents_dir = root / "adapters" / "cursor" / "agents"
    for path in sorted(modules_dir.glob("*.md")):
        if path.stem in PROCEDURE_MODULES:
            continue
        rel = path.relative_to(root).as_posix()
        text = _read(path)
        meta = parse_frontmatter(text)
        for key in ("id", "title", "auditor", "discovery"):
            if not meta.get(key):
                errors.append(f"{rel}: frontmatter is missing '{key}'")
        headings = re.findall(r"^## (.+?)\s*$", text, re.MULTILINE)
        pillar_headings = [h for h in headings if h in PILLARS]
        if pillar_headings != PILLARS:
            missing = [p for p in PILLARS if p not in headings]
            errors.append(f"{rel}: pillar headings missing or out of order" + (f" (missing: {', '.join(missing)})" if missing else ""))
        prefix = meta.get("id", "")
        allowed = tuple(p + "-" for p in (prefix, *EXTRA_RULE_PREFIXES.get(prefix, ())))
        for rule in sorted(set(re.findall(r"\bRG-[A-Z]+-\d{3}\b", text))):
            if prefix and not rule.startswith(allowed):
                errors.append(f"{rel}: rule {rule} does not match module id {prefix}")
        auditor = meta.get("auditor", "")
        if auditor and auditor not in AUDITORS:
            errors.append(f"{rel}: unknown auditor '{auditor}'")
        elif auditor and f"{path.name}" not in _read(agents_dir / f"railguards-auditor-{auditor}.md"):
            errors.append(f"{rel}: auditor '{auditor}' subagent does not reference {path.name}")
    return errors


def check_mirrors(root: Path) -> list[str]:
    errors = []
    cursor_dir, claude_dir = root / "adapters" / "cursor" / "agents", root / "adapters" / "claude-code" / "agents"
    cursor_names = {p.name for p in cursor_dir.glob("*.md")}
    claude_names = {p.name for p in claude_dir.glob("*.md")}
    for name in sorted(cursor_names ^ claude_names):
        errors.append(f"subagent {name} exists for only one tool")
    for name in sorted(cursor_names & claude_names):
        c_fm, c_body = _split_frontmatter(_read(cursor_dir / name))
        k_fm, k_body = _split_frontmatter(_read(claude_dir / name))
        if c_body.strip() != k_body.strip():
            errors.append(f"subagent {name}: Cursor and Claude Code bodies differ")
        c_meta, k_meta = parse_frontmatter(_read(cursor_dir / name)), parse_frontmatter(_read(claude_dir / name))
        for key in ("name", "description"):
            if c_meta.get(key) != k_meta.get(key):
                errors.append(f"subagent {name}: '{key}' differs between Cursor and Claude Code")
        if c_meta.get("name") != Path(name).stem:
            errors.append(f"subagent {name}: name '{c_meta.get('name')}' does not match the file name")
    rule = root / "adapters" / "cursor" / "rules" / "railguards.mdc"
    try:
        _, rule_body = _split_frontmatter(_read(rule))
        if rule_body.strip() != core_block_body(root).strip():
            errors.append("adapters/cursor/rules/railguards.mdc is out of sync with the AGENTS.md RAILGUARDS block")
        if parse_frontmatter(_read(rule)).get("alwaysApply") not in (True, "true"):
            errors.append("adapters/cursor/rules/railguards.mdc must set alwaysApply: true")
    except (OSError, ValueError) as exc:
        errors.append(f"Cursor rule mirror: {exc}")
    return errors


def check_skills(root: Path) -> list[str]:
    errors = []
    for skill in sorted((root / "skills").iterdir()):
        if not skill.is_dir():
            continue
        rel = skill.relative_to(root).as_posix()
        manifest = skill / "SKILL.md"
        if not manifest.is_file():
            errors.append(f"{rel}: missing SKILL.md")
            continue
        meta = parse_frontmatter(_read(manifest))
        name, description = str(meta.get("name", "")), str(meta.get("description", ""))
        if name != skill.name or not SKILL_NAME.match(name) or len(name) > 64:
            errors.append(f"{rel}/SKILL.md: name must be '{skill.name}' (lowercase, hyphens, at most 64 characters)")
        if not description or len(description) > 1024:
            errors.append(f"{rel}/SKILL.md: description must be 1 to 1024 characters")
    return errors


def check_json(root: Path) -> list[str]:
    errors = []
    paths = [root / "adapters" / "cursor" / "hooks.json", root / "adapters" / "claude-code" / "settings.json"]
    paths += sorted((root / "evals" / "fixtures").glob("*/expected.json"))
    for path in paths:
        try:
            json.loads(_read(path))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.relative_to(root).as_posix()}: {exc}")
    return errors


CHECKS = {
    "always-on budget": check_budget,
    "hidden Unicode": check_unicode,
    "pillar completeness": check_pillars,
    "adapter mirrors": check_mirrors,
    "skill frontmatter": check_skills,
    "JSON configs": check_json,
}


def run_all(root: Path) -> dict[str, list[str]]:
    return {name: check(Path(root)) for name, check in CHECKS.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    failed = False
    for name, errors in run_all(args.root.resolve()).items():
        print(f"{'FAIL' if errors else 'ok  '} {name}")
        for error in errors:
            print(f"     {error}")
        failed = failed or bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
