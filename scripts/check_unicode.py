#!/usr/bin/env python3
"""Find invisible and bidirectional Unicode characters that can hide instructions.

Targets "rules file backdoor" and ASCII-smuggling attacks against AI agents:
bidi controls, zero-width characters, Unicode tag characters (decoded and
shown), and other invisible code points. Emoji variation selectors
(U+FE00-U+FE0F) are allowed; a byte-order mark is allowed only at the start
of a file.

Usage:
  check_unicode.py [PATH ...] [--json]
Exit status is 1 when anything is found.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from pathlib import Path

BIDI = {0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)}
ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF}
OTHER_INVISIBLE = {
    0x00AD, 0x034F, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x180E,
    *range(0x2061, 0x2065), 0x3164, 0xFFA0, *range(0xFFF9, 0xFFFC),
}
TAGS = range(0xE0000, 0xE0080)
VARIATION_SUPPLEMENT = range(0xE0100, 0xE01F0)

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".next", "target"}
MAX_BYTES = 2_000_000


def classify(cp: int) -> str | None:
    if cp in BIDI:
        return "bidi"
    if cp in ZERO_WIDTH:
        return "zero-width"
    if cp in TAGS:
        return "tag"
    if cp in VARIATION_SUPPLEMENT:
        return "variation-selector"
    if cp in OTHER_INVISIBLE:
        return "invisible"
    return None


def scan_text(text: str) -> list[dict]:
    findings = []
    line, col = 1, 0
    for index, char in enumerate(text):
        if char == "\n":
            line, col = line + 1, 0
            continue
        col += 1
        cp = ord(char)
        category = classify(cp)
        if category is None or (cp == 0xFEFF and index == 0):
            continue
        findings.append(
            {
                "line": line,
                "col": col,
                "codepoint": f"U+{cp:04X}",
                "name": unicodedata.name(char, "UNKNOWN"),
                "category": category,
            }
        )
    return findings


def decode_tags(text: str) -> list[str]:
    """Return ASCII messages hidden as runs of Unicode tag characters."""
    messages, current = [], []
    for char in text:
        cp = ord(char)
        if 0xE0020 <= cp <= 0xE007E:
            current.append(chr(cp - 0xE0000))
        elif current:
            messages.append("".join(current))
            current = []
    if current:
        messages.append("".join(current))
    return messages


def iter_files(paths: list[str]):
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            yield path
        elif path.is_dir():
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for name in filenames:
                    yield Path(dirpath) / name


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan_paths(paths: list[str]) -> list[dict]:
    results = []
    for path in iter_files(paths):
        text = read_text(path)
        if not text:
            continue
        for finding in scan_text(text):
            results.append({"file": str(path), **finding})
        for message in decode_tags(text):
            results.append({"file": str(path), "line": 0, "col": 0, "codepoint": "TAGS", "name": f"hidden text: {message!r}", "category": "tag-decoded"})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", default=["."])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    results = scan_paths(args.paths)
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"{r['file']}:{r['line']}:{r['col']}: {r['codepoint']} {r['name']} [{r['category']}]")
        if results:
            print(f"\n{len(results)} hidden or bidirectional character(s) found.", file=sys.stderr)
    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
