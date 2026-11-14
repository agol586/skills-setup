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
    def test_agent_level_negations_cannot_reinclude_installed_skills(self) -> None:
        for agent in SETUP.AGENTS:
            with self.subTest(agent=agent), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                subprocess.run(["git", "init", "-q", directory], check=True)
                roots = {".agents", SETUP.AGENTS[agent]["dir"]}
                artifacts = []
                project_files = []
                for root in roots:
                    parent = project / root
                    parent.mkdir()
                    (parent / ".gitignore").write_text("/skills/\n!/skills/\n", encoding="utf-8")
                    artifacts.append(f"{root}/skills/ponytail/templates/base.md")
                    project_files.append(f"{root}/config.json")
                SETUP.ignore_install_artifacts(project, agent, ["ponytail"], True)
                self.assertFalse((project / ".gitignore").exists())
                for root in roots:
                    self.assertEqual((project / root / ".gitignore").read_text(), "/skills/\n!/skills/\n")
                SETUP.ignore_install_artifacts(project, agent, ["ponytail"], False)
                before = {p: p.read_bytes() for p in project.rglob(".gitignore")}
                SETUP.ignore_install_artifacts(project, agent, ["ponytail"], False)
                self.assertEqual(before, {p: p.read_bytes() for p in before})
                for name in artifacts + project_files:
                    path = project / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("content\n", encoding="utf-8")
                ignored = subprocess.run(["git", "check-ignore", "--stdin"], cwd=project,
                                         input="\n".join(artifacts + project_files) + "\n",
                                         capture_output=True, text=True, check=True)
                self.assertEqual(set(ignored.stdout.splitlines()), set(artifacts))

    def test_agent_ignore_symlink_is_rejected_before_root_ignore_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            project = Path(directory)
            outside = Path(external) / "ignore"
            outside.write_text("!/skills/\n", encoding="utf-8")
            (project / ".agents").mkdir()
            (project / ".agents" / ".gitignore").symlink_to(outside)
            with patch.object(SETUP, "run") as run:
                self.assertEqual(SETUP.main(["install", "--project", directory, "--only", "ui-ux-pro-max", "--yes"]), 1)
                run.assert_not_called()
            self.assertFalse((project / ".gitignore").exists())
            self.assertEqual(outside.read_text(), "!/skills/\n")

    def test_internal_skill_root_links_are_rejected_before_any_changes(self) -> None:
        for agent in SETUP.AGENTS:
            roots = {".agents", SETUP.AGENTS[agent]["dir"]}
            for root in roots:
                for link_parent in (False, True):
                    with self.subTest(agent=agent, root=root, link_parent=link_parent), tempfile.TemporaryDirectory() as directory:
                        project = Path(directory)
                        actual = project / "local-skills"
                        actual.mkdir()
                        sentinel = actual / "project-rule.md"
                        sentinel.write_text("keep\n", encoding="utf-8")
                        link = project / root if link_parent else project / root / "skills"
                        link.parent.mkdir(parents=True, exist_ok=True)
                        link.symlink_to(actual, target_is_directory=True)
                        ignore = project / ".gitignore"
                        ignore.write_text("dist/\n", encoding="utf-8")
                        with patch.object(SETUP, "run") as run:
                            result = SETUP.main(["install", "--project", directory, "--agent", agent,
                                                 "--only", "ui-ux-pro-max", "--yes"])
                        self.assertEqual(result, 1)
                        run.assert_not_called()
                        self.assertEqual(ignore.read_text(), "dist/\n")
                        self.assertTrue(link.is_symlink())
                        self.assertEqual(sentinel.read_text(), "keep\n")
                        self.assertEqual(list(actual.iterdir()), [sentinel])

    def test_install_rules_override_existing_negations_and_remain_repeatable(self) -> None:
        for negations in ("!/.agents/skills/\n!/skills-lock.json\n", "!*\n"):
            with self.subTest(negations=negations), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                subprocess.run(["git", "init", "-q", directory], check=True)
                ignore = project / ".gitignore"
                original = "dist/\n/.agents/skills/\n/skills-lock.json\n" + negations
                ignore.write_text(original, encoding="utf-8")
                SETUP.ignore_install_artifacts(project, "codex", ["ponytail"], True)
                self.assertEqual(ignore.read_text(), original)
                SETUP.ignore_install_artifacts(project, "codex", ["ponytail"], False)
                first = ignore.read_bytes()
                SETUP.ignore_install_artifacts(project, "codex", ["ponytail"], False)
                self.assertEqual(ignore.read_bytes(), first)
                self.assertTrue(first.startswith(original.encode()))
                artifacts = [".agents/skills/ponytail/SKILL.md", ".agents/skills/ponytail/templates/base.md", "skills-lock.json"]
                project_files = ["AGENTS.md", ".codex/config.toml", "templates/project.html"]
                for name in artifacts + project_files:
                    path = project / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("content\n", encoding="utf-8")
                ignored = subprocess.run(["git", "check-ignore", "--stdin"], cwd=project,
                                         input="\n".join(artifacts + project_files) + "\n",
                                         capture_output=True, text=True, check=True)
                self.assertEqual(set(ignored.stdout.splitlines()), set(artifacts))

    def test_install_ignores_dependencies_but_keeps_project_changes_visible(self) -> None:
        for agent in SETUP.AGENTS:
            with self.subTest(agent=agent), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                subprocess.run(["git", "init", "-q", directory], check=True)
                (project / ".gitignore").write_text("dist/\n", encoding="utf-8")
                artifacts = list(dict.fromkeys([
                    ".agents/skills/design-taste-frontend/SKILL.md",
                    f"{SETUP.AGENTS[agent]['dir']}/skills/design-taste-frontend/templates/base.md",
                    "skills-lock.json",
                ]))
                project_files = ["AGENTS.md", "docs/agents/domain.md", ".codex/config.toml",
                                 ".cursor/mcp.json", ".mcp.json", "templates/project.html", ".gitignore"]
                def fake_install(target: Path, selected_agent: str, dry_run: bool) -> None:
                    self.assertIn("/skills-lock.json", (target / ".gitignore").read_text())
                    for name in artifacts + project_files[:-1]:
                        path = target / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text("content\n", encoding="utf-8")
                args = ["install", "--project", directory, "--agent", agent, "--only", "taste-skill", "--yes"]
                with patch.dict(SETUP.INSTALLERS, {"taste-skill": fake_install}):
                    self.assertEqual(SETUP.main(args), 0)
                    first = (project / ".gitignore").read_bytes()
                    self.assertEqual(SETUP.main(args), 0)
                    self.assertEqual((project / ".gitignore").read_bytes(), first)
                ignored = subprocess.run(["git", "check-ignore", "--stdin"], cwd=project,
                                         input="\n".join(artifacts + project_files) + "\n",
                                         capture_output=True, text=True, check=True)
                self.assertEqual(set(ignored.stdout.splitlines()), set(artifacts))
                self.assertTrue(first.startswith(b"dist/\n"))

    def test_failed_install_still_ignores_partial_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            def fail_install(target: Path, agent: str, dry_run: bool) -> None:
                path = SETUP.skill_path(target, agent, "design-taste-frontend")
                path.parent.mkdir(parents=True)
                path.write_text("partial install\n", encoding="utf-8")
                raise RuntimeError("upstream failed")
            with patch.dict(SETUP.INSTALLERS, {"taste-skill": fail_install}):
                self.assertEqual(SETUP.main(["install", "--project", directory, "--only", "taste-skill", "--yes"]), 1)
            self.assertIn("/.agents/skills/", (project / ".gitignore").read_text())

    def test_skill_only_preflight_rejects_gitignore_symlink_before_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            project = Path(directory)
            outside = Path(external) / "ignore"
            outside.write_text("dist/\n", encoding="utf-8")
            (project / ".gitignore").symlink_to(outside)
            with patch.dict(SETUP.INSTALLERS, {"taste-skill": lambda *args: self.fail("Installer must not run")}):
                self.assertEqual(SETUP.main(["install", "--project", directory, "--only", "taste-skill", "--yes"]), 1)
            self.assertEqual(outside.read_text(), "dist/\n")

    def test_removed_spec_kit_selection_is_rejected_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--project", directory, "--only", "spec-kit", "--yes"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unknown catalog item: spec-kit", result.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_ponytail_only_dry_run_supports_each_agent(self) -> None:
        for agent in SETUP.AGENTS:
            with self.subTest(agent=agent), tempfile.TemporaryDirectory() as directory:
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "install", "--project", directory, "--agent", agent,
                     "--only", "ponytail", "--yes", "--dry-run"],
                    capture_output=True, text=True, check=True,
                )
                self.assertIn(f"add DietrichGebert/ponytail --skill '*' --agent {agent} --yes", result.stdout)
                self.assertNotIn("add mattpocock/skills", result.stdout)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_ponytail_upstream_discovery_requires_core_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(SETUP, "require"), \
             patch.object(SETUP, "capture_npx", return_value="│    ponytail\n│    ponytail-review\n") as capture:
            self.assertEqual(SETUP.pack_skill_names(Path(directory), "ponytail"), ["ponytail", "ponytail-review"])
            self.assertIn("DietrichGebert/ponytail", capture.call_args.args[0])
            capture.return_value = "No skills found\n"
            with self.assertRaisesRegex(RuntimeError, "Could not identify"):
                SETUP.pack_skill_names(Path(directory), "ponytail")

    def test_ponytail_recovery_preserves_customizations_and_is_repeatable(self) -> None:
        for agent in SETUP.AGENTS:
            with self.subTest(agent=agent), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                existing = SETUP.skill_path(project, agent, "ponytail")
                existing.parent.mkdir(parents=True)
                existing.write_text("project customization\n", encoding="utf-8")
                sources = {"ponytail": {"source": "https://github.com/dietrichgebert/ponytail.git/"}}
                lock = project / "skills-lock.json"
                lock.write_text(json.dumps({"skills": sources}), encoding="utf-8")
                def fake_run(command: list[str], target: Path, dry_run: bool) -> None:
                    self.assertEqual(command[command.index("--skill") + 1:command.index("--agent")], ["ponytail-review"])
                    installed = SETUP.skill_path(target, agent, "ponytail-review")
                    installed.parent.mkdir(parents=True)
                    installed.write_text("upstream review\n", encoding="utf-8")
                    sources["ponytail-review"] = {"source": "DietrichGebert/ponytail"}
                    lock.write_text(json.dumps({"skills": sources}), encoding="utf-8")
                with patch.object(SETUP, "pack_skill_names", return_value=["ponytail", "ponytail-review"]), \
                     patch.object(SETUP, "run", side_effect=fake_run) as run, patch.object(SETUP, "require"), ExitStack() as stack:
                    plan = SETUP.prepare_selected(project, agent, ["ponytail"], False, stack)["ponytail"]
                    SETUP.install_skill_pack(project, agent, False, "ponytail", plan)
                    plan = SETUP.prepare_selected(project, agent, ["ponytail"], False, stack)["ponytail"]
                    self.assertEqual(plan, [])
                    SETUP.install_skill_pack(project, agent, False, "ponytail", plan)
                    run.assert_called_once()
                self.assertEqual(existing.read_text(encoding="utf-8"), "project customization\n")

    def test_ponytail_conflict_stops_install_before_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            custom = SETUP.skill_path(project, "codex", "ponytail-review")
            custom.parent.mkdir(parents=True)
            custom.write_text("team review\n", encoding="utf-8")
            with patch.object(SETUP, "pack_skill_names", return_value=["ponytail", "ponytail-review"]), \
                 patch.object(SETUP, "run") as run:
                self.assertEqual(SETUP.main(["install", "--project", directory, "--only", "ponytail", "--yes"]), 1)
                run.assert_not_called()
            self.assertEqual(custom.read_text(encoding="utf-8"), "team review\n")

    def test_ponytail_incomplete_install_is_not_reported_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(SETUP, "run"), patch.object(SETUP, "require"):
            with self.assertRaisesRegex(RuntimeError, "not all installed"):
                SETUP.install_skill_pack(Path(directory), "codex", False, "ponytail", ["ponytail", "ponytail-review"])

    def test_default_dry_run_lists_every_item_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "install", "--project", str(project), "--agent", "codex", "--yes", "--dry-run"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Selected: matt-pocock-skills, ponytail, codegraph, archify, ui-ux-pro-max, taste-skill", result.stdout)
            self.assertNotIn("specify", result.stdout)
            self.assertIn("add DietrichGebert/ponytail --skill", result.stdout)
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

    def test_matt_preflight_blocks_existing_unowned_skill_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            custom = project / ".agents" / "skills" / "triage" / "SKILL.md"
            custom.parent.mkdir(parents=True)
            custom.write_text("team triage\n", encoding="utf-8")
            with patch.object(SETUP, "pack_skill_names", return_value=["setup-matt-pocock-skills", "triage"]), ExitStack() as stack:
                with self.assertRaisesRegex(RuntimeError, "name conflicts"):
                    SETUP.prepare_selected(project, "codex", ["matt-pocock-skills"], False, stack)
            self.assertEqual(custom.read_text(encoding="utf-8"), "team triage\n")
            self.assertFalse((project / ".specify").exists())

    def test_matt_lock_source_accepts_github_url_form(self) -> None:
        self.assertTrue(SETUP.matches_source("https://github.com/mattpocock/skills.git/", "mattpocock/skills"))
        self.assertFalse(SETUP.matches_source("other-team/skills", "mattpocock/skills"))

    def test_matt_recovery_installs_only_missing_pack_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            existing = project / ".agents" / "skills" / "setup-matt-pocock-skills" / "SKILL.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("project customization\n", encoding="utf-8")
            (project / "skills-lock.json").write_text(json.dumps({"skills": {"setup-matt-pocock-skills": {"source": "mattpocock/skills"}}}), encoding="utf-8")
            with patch.object(SETUP, "pack_skill_names", return_value=["setup-matt-pocock-skills", "triage"]), ExitStack() as stack:
                plan = SETUP.prepare_selected(project, "codex", ["matt-pocock-skills"], False, stack)["matt-pocock-skills"]
            self.assertEqual(plan, ["triage"])
            commands: list[list[str]] = []
            def fake_run(command: list[str], target: Path, dry_run: bool) -> None:
                commands.append(command)
                installed = project / ".agents" / "skills" / "triage" / "SKILL.md"
                installed.parent.mkdir(parents=True)
                installed.write_text("upstream triage\n", encoding="utf-8")
            with patch.object(SETUP, "run", side_effect=fake_run):
                SETUP.install_skill_pack(project, "codex", False, "matt-pocock-skills", plan)
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
