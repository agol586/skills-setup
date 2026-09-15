from __future__ import annotations

import importlib.util
from contextlib import ExitStack
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "setup.py"
SPEC = importlib.util.spec_from_file_location("skills_setup", SCRIPT)
assert SPEC and SPEC.loader
SETUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SETUP)


class SetupBehaviorTests(unittest.TestCase):
    def test_default_dry_run_lists_every_item_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--project", str(project), "--agent", "codex", "--yes", "--dry-run"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Selected: spec-kit, matt-pocock-skills, codegraph, archify, ui-ux-pro-max, taste-skill", result.stdout)
            self.assertIn("specify init --here", result.stdout)
            self.assertIn("uipro init --ai codex", result.stdout)
            self.assertIn("--skill design-taste-frontend", result.stdout)
            self.assertEqual(list(project.iterdir()), [])

    def test_explicit_selection_does_not_install_other_items(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--project", directory, "--only", "archify", "--yes", "--dry-run"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Selected: archify", result.stdout)
            self.assertNotIn("specify init", result.stdout)
            self.assertNotIn("codegraph init", result.stdout)

    def test_new_design_skills_can_be_selected_without_the_original_pack(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--project", directory, "--only", "ui-ux-pro-max,taste-skill", "--yes", "--dry-run"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Selected: ui-ux-pro-max, taste-skill", result.stdout)
            self.assertIn("uipro init --ai codex", result.stdout)
            self.assertIn("--skill design-taste-frontend", result.stdout)
            self.assertNotIn("specify init", result.stdout)

    def test_registered_spec_kit_integration_uses_recovery_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            metadata = project / ".specify" / "integration.json"
            metadata.parent.mkdir()
            metadata.write_text(json.dumps({"installed_integrations": ["codex"]}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--project", directory, "--only", "spec-kit", "--yes", "--dry-run"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("specify integration upgrade codex", result.stdout)
            self.assertNotIn("specify integration install codex", result.stdout)

    def test_gitignore_update_preserves_existing_rules_and_is_repeatable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            ignore = project / ".gitignore"
            ignore.write_text("dist/\n", encoding="utf-8")
            SETUP.ensure_gitignore(project, [".codegraph/"], False)
            first = ignore.read_text(encoding="utf-8")
            SETUP.ensure_gitignore(project, [".codegraph/"], False)
            self.assertEqual(ignore.read_text(encoding="utf-8"), first)
            self.assertIn("dist/", first)
            self.assertEqual(first.count(".codegraph/"), 1)

    def test_inspect_reports_established_project_without_changing_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "README.md").write_text("Released app\n", encoding="utf-8")
            (project / "AGENTS.md").write_text("Keep API compatibility\n", encoding="utf-8")
            (project / "src").mkdir()
            source = project / "src" / "app.py"
            source.write_text("def handle_request():\n    return 200\n", encoding="utf-8")
            existing = project / ".agents" / "skills" / "existing-team-skill"
            existing.mkdir(parents=True)
            (existing / "SKILL.md").write_text("Existing team rule\n", encoding="utf-8")
            before = {str(path.relative_to(project)): path.read_bytes() for path in project.rglob("*") if path.is_file()}
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "inspect", "--project", directory, "--agent", "codex"],
                capture_output=True, text=True, check=True,
            )
            after = {str(path.relative_to(project)): path.read_bytes() for path in project.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertIn("Existing project evidence: README.md, AGENTS.md", result.stdout)
            self.assertIn("Existing codex skills (1): existing-team-skill", result.stdout)
            self.assertIn("docs/brownfield.md", result.stdout)

    def test_partial_spec_kit_project_is_not_marked_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            skill = project / ".agents" / "skills" / "speckit-specify" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("existing integration\n", encoding="utf-8")
            self.assertEqual(SETUP.status(project, "codex", "spec-kit"), "integration files exist; project missing")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--project", directory, "--only", "spec-kit", "--yes", "--dry-run"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Restore .specify/", result.stderr)
            self.assertFalse((project / ".specify").exists())

    def test_spec_kit_manifest_missing_one_skill_uses_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            manifest = project / ".specify" / "integrations" / "codex.manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({"files": {
                ".agents/skills/speckit-specify/SKILL.md": "hash",
                ".agents/skills/speckit-plan/SKILL.md": "hash",
            }}), encoding="utf-8")
            shared = project / ".specify" / "integrations" / "speckit.manifest.json"
            shared.write_text(json.dumps({"files": {".specify/templates/spec-template.md": "hash"}}), encoding="utf-8")
            (project / ".specify" / "templates").mkdir()
            (project / ".specify" / "templates" / "spec-template.md").write_text("template\n", encoding="utf-8")
            (project / ".specify" / "integration.json").write_text(json.dumps({"installed_integrations": ["codex"]}), encoding="utf-8")
            primary = project / ".agents" / "skills" / "speckit-specify" / "SKILL.md"
            primary.parent.mkdir(parents=True)
            primary.write_text("existing\n", encoding="utf-8")
            self.assertNotEqual(SETUP.status(project, "codex", "spec-kit"), "ready")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--project", directory, "--only", "spec-kit", "--yes", "--dry-run"],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("specify integration upgrade codex", result.stdout)

    def test_spec_kit_missing_shared_template_uses_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            manifests = project / ".specify" / "integrations"
            manifests.mkdir(parents=True)
            (manifests / "speckit.manifest.json").write_text(json.dumps({"files": {".specify/templates/plan-template.md": "hash"}}), encoding="utf-8")
            (manifests / "codex.manifest.json").write_text(json.dumps({"files": {".agents/skills/speckit-specify/SKILL.md": "hash"}}), encoding="utf-8")
            (project / ".specify" / "integration.json").write_text(json.dumps({"installed_integrations": ["codex"]}), encoding="utf-8")
            primary = project / ".agents" / "skills" / "speckit-specify" / "SKILL.md"
            primary.parent.mkdir(parents=True)
            primary.write_text("existing\n", encoding="utf-8")
            self.assertNotEqual(SETUP.status(project, "codex", "spec-kit"), "ready")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--project", directory, "--only", "spec-kit", "--yes", "--dry-run"],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("specify integration upgrade codex", result.stdout)

    def test_spec_kit_missing_registration_uses_install_even_with_all_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            manifests = project / ".specify" / "integrations"
            manifests.mkdir(parents=True)
            (manifests / "speckit.manifest.json").write_text(json.dumps({"files": {".specify/templates/plan-template.md": "hash"}}), encoding="utf-8")
            (manifests / "codex.manifest.json").write_text(json.dumps({"files": {".agents/skills/speckit-specify/SKILL.md": "hash"}}), encoding="utf-8")
            template = project / ".specify" / "templates" / "plan-template.md"
            template.parent.mkdir()
            template.write_text("existing template\n", encoding="utf-8")
            primary = project / ".agents" / "skills" / "speckit-specify" / "SKILL.md"
            primary.parent.mkdir(parents=True)
            primary.write_text("existing skill\n", encoding="utf-8")
            self.assertNotEqual(SETUP.status(project, "codex", "spec-kit"), "ready")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--project", directory, "--only", "spec-kit", "--yes", "--dry-run"],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("specify integration install codex", result.stdout)

    def test_any_spec_kit_remnant_blocks_forced_init_without_project_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            remnant = project / ".agents" / "skills" / "speckit-plan" / "SKILL.md"
            remnant.parent.mkdir(parents=True)
            remnant.write_text("old plan skill\n", encoding="utf-8")
            with ExitStack() as stack, self.assertRaisesRegex(RuntimeError, "project directory is missing"):
                SETUP.prepare_selected(project, "codex", ["spec-kit"], False, stack)
            self.assertEqual(remnant.read_text(encoding="utf-8"), "old plan skill\n")

    def test_first_spec_kit_run_uses_uv_runner_when_tool_bin_is_not_on_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            calls: list[list[str]] = []
            with patch.object(SETUP.shutil, "which", side_effect=lambda name: None if name == "specify" else "/usr/bin/uv"), \
                 patch.object(SETUP, "run", side_effect=lambda command, project, dry_run: calls.append(command)):
                SETUP.install_spec_kit(Path(directory), "codex", True)
            self.assertIn(["uv", "tool", "install", "specify-cli"], calls)
            self.assertEqual(calls[-1][:6], ["uv", "tool", "run", "--from", "specify-cli", "specify"])
            self.assertEqual(calls[-1][6:8], ["init", "--here"])

    def test_matt_preflight_blocks_existing_unowned_skill_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            custom = project / ".agents" / "skills" / "triage" / "SKILL.md"
            custom.parent.mkdir(parents=True)
            custom.write_text("team triage\n", encoding="utf-8")
            with patch.object(SETUP, "matt_skill_names", return_value=["setup-matt-pocock-skills", "triage"]), ExitStack() as stack:
                with self.assertRaisesRegex(RuntimeError, "name conflicts"):
                    SETUP.prepare_selected(project, "codex", ["matt-pocock-skills"], False, stack)
            self.assertEqual(custom.read_text(encoding="utf-8"), "team triage\n")
            self.assertFalse((project / ".specify").exists())

    def test_matt_lock_source_accepts_github_url_form(self) -> None:
        self.assertTrue(SETUP.is_matt_source("https://github.com/mattpocock/skills.git/"))
        self.assertFalse(SETUP.is_matt_source("other-team/skills"))

    def test_matt_recovery_installs_only_missing_pack_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            existing = project / ".agents" / "skills" / "setup-matt-pocock-skills" / "SKILL.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("project customization\n", encoding="utf-8")
            (project / "skills-lock.json").write_text(json.dumps({"skills": {"setup-matt-pocock-skills": {"source": "mattpocock/skills"}}}), encoding="utf-8")
            with patch.object(SETUP, "matt_skill_names", return_value=["setup-matt-pocock-skills", "triage"]), ExitStack() as stack:
                plan = SETUP.prepare_selected(project, "codex", ["matt-pocock-skills"], False, stack)["matt-pocock-skills"]
            self.assertEqual(plan, ["triage"])
            commands: list[list[str]] = []
            def fake_run(command: list[str], target: Path, dry_run: bool) -> None:
                commands.append(command)
                installed = project / ".agents" / "skills" / "triage" / "SKILL.md"
                installed.parent.mkdir(parents=True)
                installed.write_text("upstream triage\n", encoding="utf-8")
            with patch.object(SETUP, "run", side_effect=fake_run):
                SETUP.install_matt(project, "codex", False, plan)
            self.assertEqual(existing.read_text(encoding="utf-8"), "project customization\n")
            self.assertEqual(commands[0][commands[0].index("--skill") + 1], "triage")
            self.assertNotIn("setup-matt-pocock-skills", commands[0])

    def test_ui_ux_recovery_restores_missing_files_and_preserves_existing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as staging:
            project, stage = Path(directory), Path(staging)
            staged = stage / ".agents" / "skills"
            for name in ("ui-ux-pro-max", "design"):
                skill = staged / name / "SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text(f"upstream {name}\n", encoding="utf-8")
            script = staged / "ui-ux-pro-max" / "scripts" / "search.py"
            script.parent.mkdir()
            script.write_text("print('ok')\n", encoding="utf-8")
            customized = project / ".agents" / "skills" / "ui-ux-pro-max" / "SKILL.md"
            customized.parent.mkdir(parents=True)
            customized.write_text("team design guidance\n", encoding="utf-8")
            with patch.object(SETUP, "run"):
                SETUP.install_ui_ux_pro_max(project, "codex", False, (staged, ["design", "ui-ux-pro-max"]))
            self.assertEqual(customized.read_text(encoding="utf-8"), "team design guidance\n")
            self.assertTrue((project / ".agents" / "skills" / "design" / "SKILL.md").exists())
            self.assertTrue((project / ".agents" / "skills" / "ui-ux-pro-max" / "scripts" / "search.py").exists())

    def test_ui_ux_recovery_blocks_custom_companion_even_with_primary_present(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            primary = project / ".agents" / "skills" / "ui-ux-pro-max" / "SKILL.md"
            primary.parent.mkdir(parents=True)
            primary.write_text("existing main skill\n", encoding="utf-8")
            custom = project / ".agents" / "skills" / "design" / "SKILL.md"
            custom.parent.mkdir(parents=True)
            custom.write_text("team design skill\n", encoding="utf-8")
            def stage_uipro(command: list[str], stage: Path, dry_run: bool) -> None:
                staged = stage / ".agents" / "skills"
                for name in ("ui-ux-pro-max", "design"):
                    path = staged / name / "SKILL.md"
                    path.parent.mkdir(parents=True)
                    path.write_text(f"upstream {name}\n", encoding="utf-8")
                script = staged / "ui-ux-pro-max" / "scripts" / "search.py"
                script.parent.mkdir()
                script.write_text("print('ok')\n", encoding="utf-8")
            with patch.object(SETUP, "run", side_effect=stage_uipro), ExitStack() as stack:
                with self.assertRaisesRegex(RuntimeError, "name conflicts"):
                    SETUP.prepare_selected(project, "codex", ["ui-ux-pro-max"], False, stack)
            self.assertEqual(custom.read_text(encoding="utf-8"), "team design skill\n")

    def test_ui_ux_older_companion_identity_is_accepted_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            old = project / "old.md"
            staged = project / "staged.md"
            old.write_text("---\nname: design\nmetadata:\n  author: claudekit\n  version: 1.0\n---\nold content\n", encoding="utf-8")
            staged.write_text("---\nname: design\nmetadata:\n  author: claudekit\n  version: 2.0\n---\nnew content\n", encoding="utf-8")
            self.assertTrue(SETUP.matches_uipro_companion(old, staged))
            self.assertIn("old content", old.read_text(encoding="utf-8"))

    def test_ui_ux_nested_symlink_is_blocked_before_restore(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            project = Path(directory)
            primary = project / ".agents" / "skills" / "ui-ux-pro-max" / "SKILL.md"
            primary.parent.mkdir(parents=True)
            primary.write_text("existing main\n", encoding="utf-8")
            (primary.parent / "scripts").symlink_to(Path(external), target_is_directory=True)
            def stage_uipro(command: list[str], stage: Path, dry_run: bool) -> None:
                staged = stage / ".agents" / "skills" / "ui-ux-pro-max"
                staged.mkdir(parents=True)
                (staged / "SKILL.md").write_text("upstream main\n", encoding="utf-8")
                scripts = staged / "scripts"
                scripts.mkdir()
                (scripts / "search.py").write_text("print('ok')\n", encoding="utf-8")
            with patch.object(SETUP, "run", side_effect=stage_uipro), ExitStack() as stack:
                with self.assertRaisesRegex(RuntimeError, "resolve outside"):
                    SETUP.prepare_selected(project, "codex", ["ui-ux-pro-max"], False, stack)
            self.assertEqual(list(Path(external).iterdir()), [])

    def test_preflight_blocks_skill_root_symlink_outside_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            project = Path(directory)
            (project / ".agents").mkdir()
            (project / ".agents" / "skills").symlink_to(Path(external), target_is_directory=True)
            with ExitStack() as stack, self.assertRaisesRegex(RuntimeError, "resolves outside"):
                SETUP.prepare_selected(project, "codex", ["archify"], False, stack)
            self.assertEqual(list(Path(external).iterdir()), [])

    def test_gitignore_symlink_is_rejected_before_editing(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            project = Path(directory)
            outside = Path(external) / "ignore-rules"
            outside.write_text("dist/\n", encoding="utf-8")
            (project / ".gitignore").symlink_to(outside)
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                SETUP.ensure_gitignore(project, [".codegraph/"], False)
            self.assertEqual(outside.read_text(encoding="utf-8"), "dist/\n")

    def test_single_skill_symlink_is_rejected_before_upstream_add(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            project = Path(directory)
            target = project / ".agents" / "skills" / "design-taste-frontend"
            target.parent.mkdir(parents=True)
            target.symlink_to(Path(external), target_is_directory=True)
            with ExitStack() as stack, self.assertRaisesRegex(RuntimeError, "Selected skill path is a symlink"):
                SETUP.prepare_selected(project, "codex", ["taste-skill"], False, stack)
            self.assertTrue(target.is_symlink())

    def test_empty_codegraph_directory_is_indexed_and_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / ".codegraph").mkdir()
            commands: list[list[str]] = []
            def fake_run(command: list[str], target: Path, dry_run: bool) -> None:
                commands.append(command)
                if command == ["codegraph", "init"]:
                    (project / ".codegraph" / "codegraph.db").write_bytes(b"database")
            with patch.object(SETUP.shutil, "which", return_value="/usr/bin/codegraph"), patch.object(SETUP, "run", side_effect=fake_run):
                SETUP.install_codegraph(project, "codex", False)
            self.assertIn(["codegraph", "init"], commands)
            self.assertIn(["codegraph", "status"], commands)


if __name__ == "__main__":
    unittest.main()
