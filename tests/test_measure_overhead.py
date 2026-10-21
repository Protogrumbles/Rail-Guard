import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import measure_overhead as mo  # noqa: E402


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class MeasureOverheadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root, "AGENTS.md", "a" * 400 + "\n")
        write(self.root, "CLAUDE.md", "@AGENTS.md\n" + "c" * 80 + "\n")
        write(
            self.root,
            ".cursor/rules/always.mdc",
            "---\nalwaysApply: true\n---\n" + "r" * 800 + "\n",
        )
        write(
            self.root,
            ".cursor/rules/ondemand.mdc",
            "---\ndescription: Use for payments\nalwaysApply: false\n---\n" + "x" * 4000 + "\n",
        )
        write(
            self.root,
            ".agents/skills/demo/SKILL.md",
            "---\nname: demo\ndescription: Demo skill for tests\n---\n" + "s" * 4000 + "\n",
        )
        write(
            self.root,
            ".cursor/mcp.json",
            json.dumps({"mcpServers": {"github": {"command": "npx"}, "linear": {"url": "https://x"}}}),
        )
        write(self.root, ".mcp.json", json.dumps({"mcpServers": {"memory": {"command": "uvx"}}}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_always_on_files_counted_per_tool(self):
        result = mo.measure(self.root)
        paths = {entry["path"] for entry in result["always_on"]}
        self.assertIn("AGENTS.md", paths)
        self.assertIn(".cursor/rules/always.mdc", paths)
        self.assertIn("CLAUDE.md", paths)
        self.assertNotIn(".cursor/rules/ondemand.mdc", paths)

        cursor_total = result["per_tool"]["cursor"]
        claude_total = result["per_tool"]["claude"]
        agents_tokens = mo.estimate_tokens("a" * 400 + "\n")
        self.assertGreaterEqual(cursor_total, agents_tokens + 200)
        self.assertGreaterEqual(claude_total, agents_tokens)
        self.assertEqual(result["total_tokens"], max(cursor_total, claude_total))

    def test_claude_import_counts_agents_once(self):
        result = mo.measure(self.root)
        claude_paths = [e["path"] for e in result["always_on"] if "claude" in e["tools"]]
        self.assertEqual(claude_paths.count("AGENTS.md"), 1)

    def test_on_demand_rules_and_skills_cost_only_descriptions(self):
        result = mo.measure(self.root)
        ondemand = {e["path"]: e["tokens"] for e in result["on_demand"]}
        self.assertIn(".cursor/rules/ondemand.mdc", ondemand)
        self.assertIn(".agents/skills/demo/SKILL.md", ondemand)
        self.assertLess(ondemand[".cursor/rules/ondemand.mdc"], 50)
        self.assertLess(ondemand[".agents/skills/demo/SKILL.md"], 50)

    def test_mcp_servers_listed_with_unknown_tool_tokens(self):
        result = mo.measure(self.root)
        names = sorted(s["name"] for s in result["mcp_servers"])
        self.assertEqual(names, ["github", "linear", "memory"])
        self.assertTrue(all(s["tool_tokens"] is None for s in result["mcp_servers"]))

    def test_mcp_tool_tokens_from_lock(self):
        lock = {
            "version": 1,
            "servers": {
                "github": {
                    "tools": [{"name": "create_issue", "description": "d" * 400, "inputSchema": {}}]
                }
            },
        }
        write(self.root, ".railguards/mcp-lock.json", json.dumps(lock))
        result = mo.measure(self.root)
        github = next(s for s in result["mcp_servers"] if s["name"] == "github")
        self.assertGreater(github["tool_tokens"], 90)
        self.assertGreaterEqual(result["per_tool"]["cursor"], github["tool_tokens"])

    def test_baseline_compare(self):
        mo.save_baseline(self.root, mo.measure(self.root))
        write(self.root, ".cursor/rules/always.mdc", "---\nalwaysApply: false\ndescription: x\n---\nbody\n")
        diff = mo.compare(self.root, mo.measure(self.root))
        self.assertLess(diff["per_tool"]["cursor"]["delta"], 0)
        self.assertIn(".cursor/rules/always.mdc", diff["removed_always_on"])

    def test_compare_without_baseline_raises(self):
        with self.assertRaises(FileNotFoundError):
            mo.compare(self.root, mo.measure(self.root))


if __name__ == "__main__":
    unittest.main()
