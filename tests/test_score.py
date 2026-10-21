import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evals" / "fixtures"
sys.path.insert(0, str(ROOT / "evals"))

import score  # noqa: E402


def expected(name):
    return json.loads((FIXTURES / name / "expected.json").read_text(encoding="utf-8"))


def finding(rule_id, file, start, end=None):
    return {"rule_id": rule_id, "file": file, "line_start": start, "line_end": end or start}


WEB_PERFECT = [
    finding("RG-SQLI-001", "app.py", 28),
    finding("RG-XSS-002", "app.py", 30),
    finding("RG-LOGIC-001", "app.py", 42, 47),
    finding("RG-SECRET-001", "app.py", 8, 9),
]


class FixtureConsistencyTest(unittest.TestCase):
    def test_every_fixture_has_valid_expectations(self):
        names = sorted(p.name for p in FIXTURES.iterdir() if p.is_dir())
        self.assertEqual(names, ["llm-agent-app", "mcp-server", "poisoned-repo", "web-app"])
        for name in names:
            data = expected(name)
            ids = [item["id"] for item in data["expected"]]
            self.assertEqual(len(ids), len(set(ids)), name)
            for region in data["expected"] + data.get("must_not_flag", []):
                path = FIXTURES / name / region["file"]
                self.assertTrue(path.is_file(), f"{name}: {region['file']}")
                lines = path.read_text(encoding="utf-8").count("\n")
                self.assertLessEqual(region["line_start"], region["line_end"])
                self.assertLessEqual(region["line_end"], lines, f"{name}: {region}")
            for item in data["expected"]:
                self.assertEqual(score.module_of(item["rule"]), item["module"], f"{name}: {item['id']}")


class ScoreTest(unittest.TestCase):
    def test_perfect_report(self):
        result = score.score(WEB_PERFECT, expected("web-app"))
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["modules"]["sqli"]["recall"], 1.0)

    def test_missed_finding_lowers_recall(self):
        result = score.score(WEB_PERFECT[1:], expected("web-app"))
        self.assertEqual(result["recall"], 0.75)
        self.assertEqual(result["modules"]["sqli"]["missed"], ["sqli-search"])
        self.assertEqual(result["modules"]["sqli"]["recall"], 0.0)

    def test_false_positive_on_safe_code(self):
        result = score.score(WEB_PERFECT + [finding("RG-SQLI-001", "app.py", 35)], expected("web-app"))
        self.assertEqual(result["modules"]["sqli"]["precision"], 0.5)
        self.assertIn("parameterized", result["false_positives"][0]["why"])

    def test_duplicates_are_not_false_positives(self):
        result = score.score(WEB_PERFECT + [finding("RG-SQLI-001", "app.py", 28)], expected("web-app"))
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["duplicates"], 1)

    def test_paths_are_normalized(self):
        report = [finding("RG-SQLI-001", "evals/fixtures/web-app/app.py", 28), finding("RG-XSS-002", "./app.py", 30)]
        result = score.score(report, expected("web-app"))
        self.assertEqual(result["modules"]["sqli"]["found"], 1)
        self.assertEqual(result["modules"]["xss-ssti"]["found"], 1)
        self.assertFalse(score.same_file("other-app.py", "app.py"))

    def test_alternate_module_is_accepted(self):
        report = [finding("RG-INPUT-002", "agent.py", 28), finding("RG-LLM-002", "agent.py", 36, 43), finding("RG-LOGIC-002", "rag.py", 9)]
        result = score.score(report, expected("llm-agent-app"))
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["false_positives"], [])

    def test_optional_items_do_not_count_toward_recall(self):
        report = [finding("RG-LLM-002", "agent.py", 40), finding("RG-LLM-003", "agent.py", 28), finding("RG-LLM-006", "rag.py", 9)]
        self.assertEqual(score.score(report, expected("llm-agent-app"))["recall"], 1.0)
        with_optional = score.score(report + [finding("RG-INPUT-007", "agent.py", 18)], expected("llm-agent-app"))
        self.assertEqual(with_optional["false_positives"], [])

    def test_nearby_findings_go_to_unmatched_items_first(self):
        report = [finding("RG-MCP-007", "server.py", 12), finding("RG-MCP-001", "server.py", 12), finding("RG-MCP-008", "server.py", 30)]
        self.assertEqual(score.score(report, expected("mcp-server"))["recall"], 1.0)

    def test_zero_tolerance_regions(self):
        report = [finding("RG-SUPPLY-006", "requirements.txt", 1)]
        result = score.score(report, expected("poisoned-repo"))
        self.assertEqual(result["modules"]["agent-supply-chain"]["found"], 0)
        self.assertIn("official package", result["false_positives"][0]["why"])
        dotted = score.score([finding("RG-SUPPLY-003", ".cursor/mcp.json", 4)], expected("poisoned-repo"))
        self.assertEqual(dotted["modules"]["agent-supply-chain"]["found"], 1)

    def test_unknown_rule_ids(self):
        self.assertEqual(score.module_of("SEMGREP-123"), "unknown")
        self.assertEqual(score.module_of("rg-xss-001"), "xss-ssti")


class LoadAndCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sarif_report(self):
        sarif = {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "RAILGUARDS"}}, "results": [
            {"ruleId": "RG-SQLI-001", "level": "error", "message": {"text": "SQLi"},
             "locations": [{"physicalLocation": {"artifactLocation": {"uri": "app.py"}, "region": {"startLine": 28, "endLine": 28}}}]}
        ]}]}
        path = self.dir / "report.sarif"
        path.write_text(json.dumps(sarif), encoding="utf-8")
        self.assertEqual(score.load_report(path), [{"rule_id": "RG-SQLI-001", "title": "SQLi", "file": "app.py", "line_start": 28, "line_end": 28}])

    def test_cli_min_recall(self):
        path = self.dir / "report.json"
        path.write_text(json.dumps({"findings": WEB_PERFECT[:2]}), encoding="utf-8")
        cmd = [sys.executable, str(ROOT / "evals" / "score.py"), str(path), "--fixture", str(FIXTURES / "web-app")]
        ok = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("overall", ok.stdout)
        failing = subprocess.run(cmd + ["--min-recall", "0.8"], capture_output=True, text=True)
        self.assertEqual(failing.returncode, 1)


if __name__ == "__main__":
    unittest.main()
