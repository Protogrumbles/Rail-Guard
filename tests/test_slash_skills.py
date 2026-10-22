import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import install_helpers as ih  # noqa: E402
from measure_overhead import parse_frontmatter  # noqa: E402

COMMANDS = {
    "railguards-status": "stop",
    "railguards-security-audit": "changed files",
    "railguards-full-audit": "whole repository",
    "railguards-mcp-vet": "Do not install",
}


class SlashSkillTest(unittest.TestCase):
    def test_commands_are_manual_and_specific(self):
        for name, marker in COMMANDS.items():
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            meta = parse_frontmatter(text)
            self.assertEqual(meta["name"], name)
            self.assertEqual(meta["disable-model-invocation"], "true", name)
            self.assertIn(marker, text)
            self.assertLessEqual(len(meta["description"]), 1024)

    def test_status_does_not_start_an_audit(self):
        text = (ROOT / "skills" / "railguards-status" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Do not audit", text)
        self.assertIn("permission", text)

    def test_installer_copies_the_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            ih.install(target, {"cursor"})
            installed = {p.name for p in (target / ".agents/skills").iterdir()}
            self.assertTrue(set(COMMANDS) <= installed)


if __name__ == "__main__":
    unittest.main()
