#!/usr/bin/env python3
"""Score a RAILGUARDS audit export against a fixture's expected findings.

  score.py REPORT --fixture evals/fixtures/web-app [--json] [--min-recall 0.8]

REPORT is the audit's JSON export (railguards-report.json) or SARIF export.
A reported finding matches an expected one when both map to the same module
(by rule ID prefix), the file paths match, and the line ranges overlap within
a small tolerance. Recall and precision are reported per module.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LINE_TOLERANCE = 3
PREFIX_TO_MODULE = {
    "INPUT": "input-validation",
    "SQLI": "sqli",
    "AUTH": "auth",
    "LOGIC": "logic",
    "SSTI": "xss-ssti",
    "XSS": "xss-ssti",
    "CORS": "cors",
    "DESER": "deserialization",
    "SECRET": "secrets",
    "LLM": "llm-app-security",
    "MCP": "mcp-and-tools",
    "SUPPLY": "agent-supply-chain",
}


def module_of(rule_id: str) -> str:
    parts = str(rule_id or "").upper().split("-")
    return PREFIX_TO_MODULE.get(parts[1], "unknown") if len(parts) >= 3 and parts[0] == "RG" else "unknown"


def load_report(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "runs" in data:
        findings = []
        for run in data.get("runs", []):
            for result in run.get("results", []):
                loc = (result.get("locations") or [{}])[0].get("physicalLocation", {})
                region = loc.get("region", {})
                start = region.get("startLine", 0)
                findings.append({
                    "rule_id": result.get("ruleId", ""),
                    "title": (result.get("message") or {}).get("text", ""),
                    "file": (loc.get("artifactLocation") or {}).get("uri", ""),
                    "line_start": start,
                    "line_end": region.get("endLine", start),
                })
        return findings
    return list(data.get("findings", []))


def _norm(path: str) -> str:
    path = str(path).replace("\\", "/").removeprefix("file://")
    while path.startswith("./"):
        path = path[2:]
    return path


def same_file(reported: str, expected: str) -> bool:
    reported, expected = _norm(reported), _norm(expected)
    return reported == expected or reported.endswith("/" + expected)


def overlaps(finding: dict, region: dict) -> bool:
    start = int(finding.get("line_start") or 0)
    end = int(finding.get("line_end") or start)
    slack = region.get("tolerance", LINE_TOLERANCE)
    return start - slack <= region["line_end"] and end + slack >= region["line_start"]


def accepts(item: dict, module: str) -> bool:
    return module == item["module"] or module in item.get("also_accept", [])


def score(report: list[dict], expected: dict) -> dict:
    items = expected.get("expected", [])
    avoid = expected.get("must_not_flag", [])
    matched: dict[str, list[dict]] = {item["id"]: [] for item in items}
    false_positives, duplicates = [], []

    for finding in report:
        module = module_of(finding.get("rule_id", ""))
        candidates = [item for item in items if accepts(item, module) and same_file(finding.get("file", ""), item["file"]) and overlaps(finding, item)]
        hit = next((item for item in candidates if not matched[item["id"]]), candidates[0] if candidates else None)
        if hit is not None:
            (duplicates if matched[hit["id"]] else matched[hit["id"]]).append(finding)
            continue
        safe = next((region for region in avoid if same_file(finding.get("file", ""), region["file"]) and overlaps(finding, region)), None)
        false_positives.append({**finding, "module": module, "why": f"flags safe code: {safe['reason']}" if safe else "not in expected.json"})

    modules: dict[str, dict] = {}
    for item in items:
        row = modules.setdefault(item["module"], {"expected": 0, "found": 0, "true_positives": 0, "false_positives": 0, "missed": []})
        if not item.get("optional"):
            row["expected"] += 1
            if matched[item["id"]]:
                row["found"] += 1
            else:
                row["missed"].append(item["id"])
        if matched[item["id"]]:
            row["true_positives"] += 1
    for fp in false_positives:
        row = modules.setdefault(fp["module"], {"expected": 0, "found": 0, "true_positives": 0, "false_positives": 0, "missed": []})
        row["false_positives"] += 1
    for row in modules.values():
        row["recall"] = round(row["found"] / row["expected"], 3) if row["expected"] else None
        reported = row["true_positives"] + row["false_positives"]
        row["precision"] = round(row["true_positives"] / reported, 3) if reported else None

    total_expected = sum(r["expected"] for r in modules.values())
    total_found = sum(r["found"] for r in modules.values())
    total_tp = sum(r["true_positives"] for r in modules.values())
    return {
        "fixture": expected.get("fixture"),
        "modules": dict(sorted(modules.items())),
        "recall": round(total_found / total_expected, 3) if total_expected else None,
        "precision": round(total_tp / (total_tp + len(false_positives)), 3) if (total_tp + len(false_positives)) else None,
        "false_positives": false_positives,
        "duplicates": len(duplicates),
    }


def _pct(value) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def render(result: dict) -> str:
    lines = [f"Fixture: {result['fixture']}", f"{'module':<22}{'recall':>8}{'precision':>11}  missed"]
    for name, row in result["modules"].items():
        lines.append(f"{name:<22}{_pct(row['recall']):>8}{_pct(row['precision']):>11}  {', '.join(row['missed']) or '-'}")
    lines.append(f"{'overall':<22}{_pct(result['recall']):>8}{_pct(result['precision']):>11}")
    for fp in result["false_positives"]:
        lines.append(f"false positive: {fp.get('rule_id')} {fp.get('file')}:{fp.get('line_start')} ({fp['why']})")
    if result["duplicates"]:
        lines.append(f"duplicates (same issue reported more than once): {result['duplicates']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("report", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fixture", type=Path, help="fixture directory containing expected.json")
    group.add_argument("--expected", type=Path, help="path to an expected.json file")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--min-recall", type=float, default=None, help="exit 1 if overall recall is below this value")
    args = parser.parse_args(argv)
    expected_path = args.expected or args.fixture / "expected.json"
    result = score(load_report(args.report), json.loads(expected_path.read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2) if args.json else render(result))
    if args.min_recall is not None and (result["recall"] or 0) < args.min_recall:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
