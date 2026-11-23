from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ruamel.yaml import YAML


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install-agent-skill.py"


class AgentSkillInstallTests(unittest.TestCase):
    def test_installed_skill_keeps_workflow_and_installer_together(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory) / "skills"
            project = Path(directory) / "target"
            project.mkdir()
            subprocess.run(
                [sys.executable, str(INSTALLER), "--agent", "codex", "--skills-dir", str(skills_dir)],
                capture_output=True, text=True, check=True,
            )
            installed = skills_dir / "agent-skill-setup"
            self.assertIn("name: agent-skill-setup", (installed / "SKILL.md").read_text(encoding="utf-8"))
            self.assertIs(YAML().load(installed / "agents" / "openai.yaml")["policy"]["allow_implicit_invocation"], True)
            self.assertTrue((installed / "source" / "scripts" / "skill_visibility.py").is_file())
            self.assertTrue((installed / "source" / "requirements.txt").is_file())
            self.assertTrue((installed / "source" / "skills" / "agent-skill-setup" / "WORKFLOW.md").is_file())
            self.assertEqual(list(installed.rglob("SKILL.md")), [installed / "SKILL.md"])
            self.assertTrue((installed / "source" / "docs" / "brownfield.md").is_file())
            self.assertTrue((installed / "source" / "docs" / "initializers" / "ponytail.md").is_file())
            self.assertFalse((installed / "source" / "docs" / "initializers" / "spec-kit.md").exists())
            result = subprocess.run(
                [sys.executable, str(installed / "source" / "scripts" / "setup.py"), "list", "--project", str(project), "--agent", "codex"],
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(result.stdout.count("[x]"), 6)
            self.assertTrue(result.stdout.startswith("1. [x] Matt Pocock's skills"))
            self.assertIn("Ponytail (DietrichGebert/ponytail)", result.stdout)
            self.assertNotIn("Spec Kit", result.stdout)
            self.assertEqual(list(project.iterdir()), [])

    def test_existing_skill_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_dir = Path(directory) / "skills"
            installed = skills_dir / "agent-skill-setup"
            installed.mkdir(parents=True)
            sentinel = installed / "SKILL.md"
            sentinel.write_text("Team-customized workflow\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(INSTALLER), "--agent", "claude-code", "--skills-dir", str(skills_dir)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "Team-customized workflow\n")


if __name__ == "__main__":
    unittest.main()
