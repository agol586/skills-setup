from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from ruamel.yaml import YAML

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from skill_visibility import enable_model_invocation


class SkillVisibilityTests(unittest.TestCase):
    def create_skill(self, root: Path, name: str = "example", frontmatter: str = "") -> Path:
        skill = root / name
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Example skill\n{frontmatter}---\n"
            "# Instructions\n\nExample text: disable-model-invocation: true\n", encoding="utf-8")
        return skill

    def test_enables_both_policies_preserving_body_metadata_and_comments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = self.create_skill(root, frontmatter='disable-model-invocation: true\nmetadata:\n  author: "team" # keep author\n')
            metadata_path = skill / "agents" / "openai.yaml"
            metadata_path.parent.mkdir()
            metadata_path.write_text(
                'interface:\n  display_name: "Example" # keep label\n'
                'policy: {allow_implicit_invocation: false, products: [CODEX]}\n'
                'dependencies:\n  tools: [{type: mcp, value: docs}]\n', encoding="utf-8")
            original = (skill / "SKILL.md").read_text()
            enable_model_invocation([skill], root, False)
            manifest = (skill / "SKILL.md").read_text()
            self.assertEqual(manifest.split("---\n", 2)[2], original.split("---\n", 2)[2])
            frontmatter = YAML().load(manifest.split("---\n", 2)[1])
            self.assertNotIn("disable-model-invocation", frontmatter)
            self.assertEqual(frontmatter["metadata"]["author"], "team")
            self.assertIn("# keep author", manifest)
            metadata = YAML().load(metadata_path)
            self.assertIs(metadata["policy"]["allow_implicit_invocation"], True)
            self.assertEqual(metadata["policy"]["products"], ["CODEX"])
            self.assertEqual(metadata["dependencies"]["tools"], [{"type": "mcp", "value": "docs"}])
            self.assertIn('# keep label', metadata_path.read_text())
            before = {p: p.read_bytes() for p in skill.rglob("*") if p.is_file()}
            enable_model_invocation([skill], root, False)
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_missing_metadata_is_created_and_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = self.create_skill(root)
            original = (skill / "SKILL.md").read_bytes()
            enable_model_invocation([skill], root, True)
            self.assertFalse((skill / "agents").exists())
            enable_model_invocation([skill], root, False)
            self.assertEqual((skill / "SKILL.md").read_bytes(), original)
            self.assertIs(YAML().load(skill / "agents" / "openai.yaml")["policy"]["allow_implicit_invocation"], True)

    def test_invalid_metadata_stops_before_any_visibility_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.create_skill(root, "first", "disable-model-invocation: true\n")
            second = self.create_skill(root, "second")
            (second / "agents").mkdir()
            (second / "agents" / "openai.yaml").write_text("policy: false\n")
            before = (first / "SKILL.md").read_bytes()
            with self.assertRaisesRegex(RuntimeError, "policy mapping"):
                enable_model_invocation([first, second], root, False)
            self.assertEqual(before, (first / "SKILL.md").read_bytes())
            self.assertFalse((first / "agents").exists())

    def test_external_metadata_link_is_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            skill = self.create_skill(root, frontmatter="disable-model-invocation: true\n")
            (skill / "agents").mkdir()
            outside = Path(external) / "openai.yaml"
            outside.write_text("policy: {allow_implicit_invocation: false}\n")
            (skill / "agents" / "openai.yaml").symlink_to(outside)
            with self.assertRaisesRegex(RuntimeError, "local file review"):
                enable_model_invocation([skill], root, False)
            self.assertIn("false", outside.read_text())
            self.assertIn("disable-model-invocation: true", (skill / "SKILL.md").read_text())
