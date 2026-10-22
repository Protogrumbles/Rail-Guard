import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ci_checks  # noqa: E402

COPY = ("AGENTS.md", "skills", "adapters", "evals")


class RepoPassesTest(unittest.TestCase):
    def test_repository_passes_all_checks(self):
        self.assertEqual({name: errors for name, errors in ci_checks.run_all(ROOT).items() if errors}, {})


class DetectsProblemsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in COPY:
            src = ROOT / name
            if src.is_dir():
                shutil.copytree(src, self.root / name, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(src, self.root / name)

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, rel, transform):
        path = self.root / rel
        path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")

    def test_copy_is_clean(self):
        self.assertEqual({k: v for k, v in ci_checks.run_all(self.root).items() if v}, {})

    def test_budget(self):
        self.edit("AGENTS.md", lambda t: t.replace("## Spend", "## Spend\n" + "- filler line\n" * 40))
        self.assertTrue(any("lines" in e for e in ci_checks.check_budget(self.root)))
        self.edit("AGENTS.md", lambda t: t.replace("## Triggers", "## Triggers\n" + "word " * 6000))
        self.assertTrue(any("tokens" in e for e in ci_checks.check_budget(self.root)))

    def test_hidden_unicode(self):
        self.edit("skills/railguards-vet/SKILL.md", lambda t: t + "\nvet\u200b everything\n")
        errors = ci_checks.check_unicode(self.root)
        self.assertTrue(any("railguards-vet/SKILL.md" in e and "U+200B" in e for e in errors))

    def test_poisoned_fixture_must_keep_payload(self):
        rule = "evals/fixtures/poisoned-repo/.cursor/rules/style.mdc"
        self.edit(rule, lambda t: "".join(c for c in t if ord(c) < 0x2000))
        self.assertTrue(any("lost its payload" in e for e in ci_checks.check_unicode(self.root)))

    def test_missing_pillar(self):
        self.edit("skills/railguards-audit/modules/sqli.md", lambda t: t.replace("## S: Spend", "## Cost"))
        errors = ci_checks.check_pillars(self.root)
        self.assertTrue(any("sqli.md" in e and "S: Spend" in e for e in errors))

    def test_rule_prefix_mismatch(self):
        self.edit("skills/railguards-audit/modules/cors.md", lambda t: t + "\nSee also RG-AUTH-001.\n")
        self.assertTrue(any("RG-AUTH-001" in e for e in ci_checks.check_pillars(self.root)))

    def test_subagent_drift(self):
        self.edit("adapters/claude-code/agents/railguards-verifier.md", lambda t: t + "\nExtra instruction.\n")
        self.assertTrue(any("bodies differ" in e for e in ci_checks.check_mirrors(self.root)))

    def test_rule_mirror_drift(self):
        self.edit("AGENTS.md", lambda t: t.replace("## Spend", "## Spend\n- New habit."))
        self.assertTrue(any("out of sync" in e for e in ci_checks.check_mirrors(self.root)))

    def test_skill_name(self):
        self.edit("skills/railguards-vet/SKILL.md", lambda t: t.replace("name: railguards-vet", "name: Vet Tool", 1))
        self.assertTrue(any("railguards-vet" in e for e in ci_checks.check_skills(self.root)))


if __name__ == "__main__":
    unittest.main()
