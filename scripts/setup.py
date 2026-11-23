#!/usr/bin/env python3
"""Install this repository's catalog into an existing coding project."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from skill_visibility import check_visibility_paths, enable_model_invocation, yaml_parser

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
ITEMS = {item["id"]: item for item in CATALOG}
AGENTS = {
    "codex": {"skills": "codex", "graph": "codex", "dir": ".agents"},
    "claude-code": {"skills": "claude-code", "graph": "claude", "dir": ".claude"},
    "cursor": {"skills": "cursor", "graph": "cursor", "dir": ".cursor"},
}

PACKS = {
    "matt-pocock-skills": "setup-matt-pocock-skills",
    "ponytail": "ponytail",
}


def project_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"Project directory does not exist: {path}")
    return path


def ids_from_csv(value: str) -> list[str]:
    ids = [part.strip() for part in value.split(",") if part.strip()]
    unknown = [item_id for item_id in ids if item_id not in ITEMS]
    if unknown:
        raise argparse.ArgumentTypeError(f"Unknown catalog item: {', '.join(unknown)}")
    return ids


def skill_path(project: Path, agent: str, name: str) -> Path:
    return project / AGENTS[agent]["dir"] / "skills" / name / "SKILL.md"


def skill_dir(project: Path, agent: str, name: str) -> Path:
    return skill_path(project, agent, name).parent


def path_present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def check_local_skill_root(project: Path, agent: str) -> None:
    for directory in dict.fromkeys((".agents", AGENTS[agent]["dir"])):
        parent = project / directory
        root = parent / "skills"
        if not root.resolve().is_relative_to(project.resolve()):
            raise RuntimeError(f"Agent skill directory resolves outside the target project: {root}. Use a project-local directory before installation.")
        if parent.is_symlink() or root.is_symlink():
            raise RuntimeError(f"Agent skill root uses a symlink: {root}. Use a real project-local directory so installation artifacts can be ignored reliably.")


def check_local_gitignore(project: Path) -> None:
    path = project / ".gitignore"
    if path.is_symlink():
        raise RuntimeError(f"Target .gitignore is a symlink: {path}. Review its destination before editing ignore rules.")


def check_local_graph_index(project: Path) -> None:
    for path in (project / ".codegraph", project / ".codegraph" / "codegraph.db"):
        if path.is_symlink():
            raise RuntimeError(f"CodeGraph index path is a symlink: {path}. Use a project-local index before installation.")


def check_local_agent_config(project: Path) -> None:
    managed = ("AGENTS.md", "CLAUDE.md", ".codex/config.toml", ".cursor/mcp.json", ".mcp.json")
    for name in managed:
        path = project / name
        if path.is_symlink():
            raise RuntimeError(f"Agent configuration is a symlink: {path}. Review its destination before local MCP installation.")


def status(project: Path, agent: str, item_id: str) -> str:
    if item_id in PACKS:
        return "entry skill present; pack needs verification" if skill_path(project, agent, PACKS[item_id]).exists() else "absent"
    if item_id == "codegraph":
        database = project / ".codegraph" / "codegraph.db"
        if database.is_file() and database.stat().st_size > 0:
            return "indexed; agent config needs review"
        return "directory present; index needs repair" if (project / ".codegraph").exists() else "absent"
    if item_id == "archify":
        return "installed" if skill_path(project, agent, "archify").exists() else "absent"
    if item_id == "ui-ux-pro-max":
        return "primary present; companions need verification" if skill_path(project, agent, "ui-ux-pro-max").exists() else "absent"
    if item_id == "taste-skill":
        return "installed; design context needs review" if skill_path(project, agent, "design-taste-frontend").exists() else "absent"
    raise ValueError(item_id)


def show_catalog(project: Path, agent: str, selected: set[str] | None = None) -> None:
    for index, item in enumerate(CATALOG, 1):
        mark = "x" if selected is None or item["id"] in selected else " "
        print(f"{index}. [{mark}] {item['name']} ({item['source']}) — {status(project, agent, item['id'])}")


def inspect_project(project: Path, agent: str) -> None:
    """Print a read-only inventory before changing an established project."""
    print(f"Project preflight: {project}")
    git = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    ) if shutil.which("git") else None
    if git and git.returncode == 0:
        root = Path(git.stdout.strip()).resolve()
        print(f"Git root: {root}")
        changes = subprocess.run(
            ["git", "-C", str(project), "status", "--porcelain", "--untracked-files=normal"],
            capture_output=True, text=True, check=False,
        )
        lines = changes.stdout.splitlines()
        print(f"Existing Git changes: {len(lines)}")
        for line in lines[:20]:
            print(f"  {line}")
        if len(lines) > 20:
            print(f"  ... {len(lines) - 20} more")
        if root != project:
            print("Target is inside a larger Git checkout; review changes from its Git root.")
    else:
        print("Git root: unavailable; save a recoverable baseline before installation.")
    evidence = ["README.md", "AGENTS.md", "CLAUDE.md", "docs", ".gitignore", "package.json", "pyproject.toml", "go.mod"]
    present = [name for name in evidence if (project / name).exists()]
    print(f"Existing project evidence: {', '.join(present) if present else 'none'}")
    skills_dir = project / AGENTS[agent]["dir"] / "skills"
    existing_skills = sorted(path.name for path in skills_dir.iterdir() if path.is_dir()) if skills_dir.is_dir() else []
    print(f"Existing {agent} skills ({len(existing_skills)}): {', '.join(existing_skills[:20]) if existing_skills else 'none'}")
    if len(existing_skills) > 20:
        print(f"  ... {len(existing_skills) - 20} more")
    if present or existing_skills:
        print("Established project: preserve existing docs, app behavior, and skill customizations; use docs/brownfield.md after installation.")


def select_items(args: argparse.Namespace) -> list[str]:
    selected = set(args.only) if args.only is not None else set(ITEMS)
    selected.difference_update(args.skip or [])
    if args.command == "install" and args.only is None and not args.yes and not args.dry_run and sys.stdin.isatty():
        show_catalog(args.project, args.agent, selected)
        answer = input("输入要取消的编号（逗号分隔），直接回车保留全部：").strip()
        if answer:
            for part in answer.split(","):
                try:
                    index = int(part.strip())
                except ValueError as exc:
                    raise ValueError(f"Invalid checklist number: {part}") from exc
                if not 1 <= index <= len(CATALOG):
                    raise ValueError(f"Checklist number out of range: {index}")
                selected.discard(CATALOG[index - 1]["id"])
    return [item["id"] for item in CATALOG if item["id"] in selected]


def run(command: list[str], project: Path, dry_run: bool) -> None:
    print("$", shlex.join(command), f"(cwd: {project})", flush=True)
    if dry_run:
        return
    if command[0] in {"npm", "npx"}:
        with tempfile.TemporaryDirectory(prefix="skills-setup-npm-") as cache:
            environment = os.environ.copy()
            environment["npm_config_cache"] = cache
            subprocess.run(command, cwd=project, env=environment, check=True)
    else:
        subprocess.run(command, cwd=project, check=True)


def capture_npx(command: list[str], project: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="skills-setup-npm-") as cache:
        environment = os.environ.copy()
        environment["npm_config_cache"] = cache
        result = subprocess.run(command, cwd=project, env=environment, capture_output=True, text=True, check=True)
    return result.stdout


def locked_skill_sources(project: Path) -> dict[str, str]:
    lock = project / "skills-lock.json"
    if not lock.exists():
        return {}
    try:
        skills = json.loads(lock.read_text(encoding="utf-8")).get("skills", {})
        return {name: entry.get("source", "") for name, entry in skills.items() if isinstance(entry, dict)}
    except (OSError, ValueError, AttributeError) as exc:
        raise RuntimeError(f"Cannot read skill provenance from {lock}: {exc}") from exc


def matches_source(source: str, expected: str) -> bool:
    value = source.strip().lower().removeprefix("https://github.com/").removeprefix("http://github.com/")
    return value.rstrip("/").removesuffix(".git") == expected.lower()


def skill_identity(path: Path) -> tuple[str, str]:
    """Read the skill name and upstream author from frontmatter."""
    try:
        head = path.read_text(encoding="utf-8").split("---", 2)
        frontmatter = head[1] if len(head) > 2 else ""
        name = re.search(r"(?m)^name:\s*['\"]?([a-z][a-z0-9-]*)", frontmatter)
        author = re.search(r"(?m)^\s+author:\s*['\"]?([a-z][a-z0-9-]*)", frontmatter)
        return (name.group(1), author.group(1)) if name and author else ("", "")
    except (OSError, UnicodeError):
        return ("", "")


def matches_uipro_companion(existing: Path, staged: Path) -> bool:
    if existing.read_bytes() == staged.read_bytes():
        return True
    old_identity = skill_identity(existing)
    return old_identity[1] == "claudekit" and old_identity == skill_identity(staged)


def pack_skill_names(project: Path, item_id: str) -> list[str]:
    item = ITEMS[item_id]
    require("npx", "Install Node.js/npm before rerunning.", False)
    command = ["npx", "--yes", "skills@latest", "add", item["source"], "--list"]
    print("$", shlex.join(command), f"(cwd: {project}; read-only upstream list)", flush=True)
    output = capture_npx(command, project)
    names = list(dict.fromkeys(re.findall(r"(?m)^[│|]    ([a-z][a-z0-9-]*)\s*$", output)))
    if PACKS[item_id] not in names:
        raise RuntimeError(f"Could not identify {item['name']} complete upstream skill list; no project files were changed.")
    return names


def prepare_selected(project: Path, agent: str, selected: list[str], dry_run: bool, stack: ExitStack) -> dict[str, object]:
    """Resolve whole-pack manifests and conflicts before any target writes."""
    if dry_run:
        return {}
    check_local_gitignore(project)
    plans: dict[str, object] = {}
    if any(item_id in selected for item_id in (*PACKS, "archify", "ui-ux-pro-max", "taste-skill")):
        check_local_skill_root(project, agent)
        for directory in dict.fromkeys((".agents", AGENTS[agent]["dir"])):
            check_local_gitignore(project / directory)
        yaml_parser()
    visibility = []
    if "codegraph" in selected:
        check_local_graph_index(project)
        check_local_agent_config(project)
    for item_id, name in (("archify", "archify"), ("taste-skill", "design-taste-frontend")):
        if item_id in selected:
            visibility.append(skill_dir(project, agent, name))
        if item_id in selected and skill_dir(project, agent, name).is_symlink():
            raise RuntimeError(f"Selected skill path is a symlink: {skill_dir(project, agent, name)}. Review its destination before project-local installation.")
    for item_id in PACKS:
        if item_id not in selected:
            continue
        item = ITEMS[item_id]
        names = pack_skill_names(project, item_id)
        visibility.extend(skill_dir(project, agent, name) for name in names)
        sources = locked_skill_sources(project)
        conflicts = [name for name in names if path_present(skill_dir(project, agent, name)) and not matches_source(sources.get(name, ""), item["source"])]
        if conflicts:
            paths = ", ".join(str(skill_dir(project, agent, name)) for name in conflicts)
            raise RuntimeError(f"{item['name']} skill name conflicts with existing project skills: {paths}. Preserve or rename the existing skills before installing this pack.")
        missing = [name for name in names if not skill_path(project, agent, name).exists()]
        blocked = [name for name in missing if path_present(skill_dir(project, agent, name))]
        if blocked:
            raise RuntimeError(f"Incomplete existing {item['name']} skill directories need manual review: {', '.join(blocked)}")
        plans[item_id] = missing
        print(f"{item['name']} pack preflight: {len(names)} upstream skills, {len(missing)} missing, no name conflicts.")
    if "ui-ux-pro-max" in selected:
        stage = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="skills-setup-uipro-")))
        ai = {"codex": "codex", "claude-code": "claude", "cursor": "cursor"}[agent]
        require("npx", "Install Node.js/npm before rerunning.", False)
        run(["npx", "--yes", "--package", "ui-ux-pro-max-cli", "uipro", "init", "--ai", ai, "--offline"], stage, False)
        stage_skills = stage / AGENTS[agent]["dir"] / "skills"
        names = sorted(path.name for path in stage_skills.iterdir() if (path / "SKILL.md").exists()) if stage_skills.is_dir() else []
        if "ui-ux-pro-max" not in names or not (stage_skills / "ui-ux-pro-max" / "scripts" / "search.py").exists():
            raise RuntimeError("UI UX Pro Max staging did not produce its primary skill and search script; no project files were changed.")
        primary_present = skill_path(project, agent, "ui-ux-pro-max").exists()
        conflicts = [name for name in names if path_present(skill_dir(project, agent, name)) and
                     (name != "ui-ux-pro-max" or not primary_present) and
                     (not skill_path(project, agent, name).exists() or not matches_uipro_companion(skill_path(project, agent, name), stage_skills / name / "SKILL.md"))]
        symlinks = [name for name in names if skill_dir(project, agent, name).is_symlink()]
        if symlinks:
            raise RuntimeError(f"UI UX Pro Max skill paths are symlinks and need project-local review before restoration: {', '.join(symlinks)}")
        outside_paths = [str(skill_dir(project, agent, name) / source_file.relative_to(stage_skills / name))
                         for name in names for source_file in (stage_skills / name).rglob("*") if source_file.is_file()
                         and not (skill_dir(project, agent, name) / source_file.relative_to(stage_skills / name)).resolve().is_relative_to(project.resolve())]
        if outside_paths:
            raise RuntimeError(f"UI UX Pro Max managed files resolve outside the target project: {', '.join(outside_paths[:5])}")
        if conflicts:
            paths = ", ".join(str(skill_dir(project, agent, name)) for name in conflicts)
            raise RuntimeError(f"UI UX Pro Max name conflicts with existing project skills: {paths}. Preserve or rename the existing skills before installing this pack.")
        plans["ui-ux-pro-max"] = (stage_skills, names)
        visibility.extend(skill_dir(project, agent, name) for name in names)
        missing = [name for name in names if not skill_path(project, agent, name).exists()]
        print(f"UI UX Pro Max preflight: {len(names)} bundled skills, {len(missing)} missing, no name conflicts.")
    for skill in visibility:
        check_visibility_paths(skill, project)
    plans["visibility"] = visibility
    return plans


def require(command: str, hint: str, dry_run: bool) -> None:
    if not dry_run and shutil.which(command) is None:
        raise RuntimeError(f"Missing {command}. {hint}")


def ensure_gitignore(project: Path, entries: list[str], dry_run: bool) -> None:
    path = project / ".gitignore"
    check_local_gitignore(project)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    # A later negation can undo an earlier rule, including via a wildcard.
    # Reassert our rules after the last negation without interpreting Git globs.
    existing = set()
    for line in old.splitlines():
        if line.startswith("!"):
            existing.clear()
        else:
            existing.add(line.strip())
    missing = [entry for entry in entries if entry not in existing]
    if not missing:
        return
    print(f"Update {path}: {', '.join(missing)}")
    if dry_run:
        return
    prefix = "\n" if old and not old.endswith("\n") else ""
    separator = "\n" if old else ""
    path.write_text(old + prefix + separator + "# Generated local skill data\n" + "\n".join(missing) + "\n", encoding="utf-8")


def ignore_install_artifacts(project: Path, agent: str, selected: list[str], dry_run: bool) -> None:
    entries = []
    if any(item_id != "codegraph" for item_id in selected):
        # Skills CLI keeps canonical copies in .agents, with agent-specific links.
        entries.append("/.agents/skills/")
        entries.append("/.skills-setup/backups/")
        if AGENTS[agent]["dir"] != ".agents":
            entries.append(f"/{AGENTS[agent]['dir']}/skills/")
    if any(item_id in (*PACKS, "archify", "taste-skill") for item_id in selected):
        entries.append("/skills-lock.json")
    if "codegraph" in selected:
        entries.append("/.codegraph/")
    if entries:
        ensure_gitignore(project, entries, dry_run)
    if any(item_id != "codegraph" for item_id in selected):
        # An agent-level ignore file takes precedence over the root rules.
        for directory in dict.fromkeys((".agents", AGENTS[agent]["dir"])):
            parent = project / directory
            if path_present(parent / ".gitignore"):
                ensure_gitignore(parent, ["/skills/"], dry_run)


def install_skill_pack(project: Path, agent: str, dry_run: bool, item_id: str, missing: list[str] | None = None) -> None:
    item = ITEMS[item_id]
    if not dry_run and missing is None:
        raise RuntimeError(f"{item['name']} pack preflight is required before installation.")
    if dry_run or missing:
        require("npx", "Install Node.js/npm before rerunning.", dry_run)
        names = ["*"] if dry_run else missing
        run(["npx", "--yes", "skills@latest", "add", item["source"], "--skill", *names, "--agent", AGENTS[agent]["skills"], "--yes"], project, dry_run)
        if not dry_run and any(not skill_path(project, agent, name).exists() for name in missing):
            raise RuntimeError(f"{item['name']} selected missing skills were not all installed into the agent directory.")
    else:
        print(f"{item['name']} complete upstream pack is already present.")
    if item_id == "matt-pocock-skills":
        print("Next: invoke setup-matt-pocock-skills as the default project initializer; it is prompt-driven.")
    else:
        print(f"Next: read {item['guide']} and reconcile the installed skills with project guidance.")


def install_codegraph(project: Path, agent: str, dry_run: bool) -> None:
    check_local_graph_index(project)
    check_local_agent_config(project)
    if shutil.which("codegraph") is None:
        require("npm", "Install Node.js/npm before rerunning.", dry_run)
        run(["npm", "install", "-g", "@colbymchenry/codegraph"], project, dry_run)
        if not dry_run and shutil.which("codegraph") is None:
            prefix = subprocess.run(["npm", "prefix", "-g"], capture_output=True, text=True, check=False)
            hint = f"{prefix.stdout.strip()}/bin" if prefix.returncode == 0 else "your npm global executable directory"
            raise RuntimeError(f"CodeGraph was installed but `codegraph` is not on this process's PATH. Add {hint} to PATH and rerun so the agent's MCP config can launch it.")
    run(["codegraph", "install", f"--target={AGENTS[agent]['graph']}", "--location=local", "--yes"], project, dry_run)
    database = project / ".codegraph" / "codegraph.db"
    if not database.is_file() or database.stat().st_size == 0:
        run(["codegraph", "init"], project, dry_run)
    if not dry_run:
        if not database.is_file() or database.stat().st_size == 0:
            raise RuntimeError("CodeGraph did not create a usable project index database.")
        run(["codegraph", "status"], project, dry_run)
    ensure_gitignore(project, ["/.codegraph/"], dry_run)
    print("Next: restart the agent for its MCP integration, then verify CodeGraph can explore this project.")


def install_archify(project: Path, agent: str, dry_run: bool) -> None:
    path = skill_path(project, agent, "archify")
    if not path.exists():
        require("npx", "Install Node.js/npm before rerunning.", dry_run)
        run(["npx", "--yes", "skills@latest", "add", "tt-a1i/archify", "--skill", "archify", "--agent", AGENTS[agent]["skills"], "--yes"], project, dry_run)
    else:
        print("Archify skill already present.")
    doctor = path.parent / "bin" / "archify.mjs"
    if doctor.exists():
        require("node", "Install Node.js 18+ before rerunning.", dry_run)
        run(["node", str(doctor), "doctor"], project, dry_run)
    elif not dry_run:
        raise RuntimeError("Archify's doctor command was not found in the installed skill.")
    else:
        print("Next: verify the installed Archify skill with `node bin/archify.mjs doctor`.")


def install_ui_ux_pro_max(project: Path, agent: str, dry_run: bool, prepared: tuple[Path, list[str]] | None = None) -> None:
    path = skill_path(project, agent, "ui-ux-pro-max")
    if dry_run:
        require("npx", "Install Node.js/npm before rerunning.", dry_run)
        ai = {"codex": "codex", "claude-code": "claude", "cursor": "cursor"}[agent]
        command = ["npx", "--yes", "--package", "ui-ux-pro-max-cli", "uipro", "init", "--ai", ai, "--offline"]
        print("$", shlex.join(command), "(cwd: temporary staging directory; dry run)")
        print("Then copy only missing bundled skill files into the target project after checking name conflicts.")
    else:
        if prepared is None:
            raise RuntimeError("UI UX Pro Max staging preflight is required before installation.")
        stage_skills, names = prepared
        for name in names:
            source = stage_skills / name
            target = skill_dir(project, agent, name)
            if not path_present(target):
                print(f"Install missing UI UX Pro Max skill: {target}")
                shutil.copytree(source, target)
            else:
                for source_file in source.rglob("*"):
                    if not source_file.is_file():
                        continue
                    target_file = target / source_file.relative_to(source)
                    if not path_present(target_file):
                        print(f"Restore missing UI UX Pro Max file: {target_file}")
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_file, target_file)
        if any(not skill_path(project, agent, name).exists() for name in names):
            raise RuntimeError("UI UX Pro Max's bundled skill pack is incomplete after restoration.")
    search = path.parent / "scripts" / "search.py"
    if not dry_run and not search.exists():
        raise RuntimeError("UI UX Pro Max did not install its search script into the selected agent directory.")
    if search.exists():
        require("python3", "Python 3 is needed for the UI UX Pro Max search script.", dry_run)
        run(["python3", str(search), "responsive layout", "--domain", "ux"], project, dry_run)
    print("Next: read docs/initializers/ui-ux-pro-max.md and reconcile design guidance with project docs.")


def install_taste_skill(project: Path, agent: str, dry_run: bool) -> None:
    path = skill_path(project, agent, "design-taste-frontend")
    if not path.exists():
        require("npx", "Install Node.js/npm before rerunning.", dry_run)
        run(["npx", "--yes", "skills@latest", "add", "https://github.com/Leonxlnx/taste-skill", "--skill", "design-taste-frontend", "--agent", AGENTS[agent]["skills"], "--yes"], project, dry_run)
    else:
        print("Taste Skill already present.")
    if not dry_run and not path.exists():
        raise RuntimeError("Taste Skill was not installed into the selected agent directory.")
    print("Next: read docs/initializers/taste-skill.md and infer design dials from existing project guidance.")


INSTALLERS = {
    "codegraph": install_codegraph,
    "archify": install_archify,
    "ui-ux-pro-max": install_ui_ux_pro_max,
    "taste-skill": install_taste_skill,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("list", "inspect", "install"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--project", type=project_path, required=True)
        sub.add_argument("--agent", choices=AGENTS, default="codex")
        if command == "install":
            sub.add_argument("--only", type=ids_from_csv)
            sub.add_argument("--skip", type=ids_from_csv)
            sub.add_argument("--yes", action="store_true", help="Use the default all-selected catalog without prompting")
            sub.add_argument("--dry-run", action="store_true", help="Print commands without writes or network calls")
    args = parser.parse_args(argv)
    if args.command == "list":
        show_catalog(args.project, args.agent)
        return 0
    if args.command == "inspect":
        inspect_project(args.project, args.agent)
        return 0
    try:
        selected = select_items(args)
        if not selected:
            print("Nothing selected.")
            return 0
        print(f"Target: {args.project} | Agent: {args.agent} | Selected: {', '.join(selected)}")
        inspect_project(args.project, args.agent)
        with ExitStack() as stack:
            plans = prepare_selected(args.project, args.agent, selected, args.dry_run, stack)
            ignore_install_artifacts(args.project, args.agent, selected, args.dry_run)
            for item_id in selected:
                if item_id in PACKS:
                    install_skill_pack(args.project, args.agent, args.dry_run, item_id, plans.get(item_id))
                elif item_id == "ui-ux-pro-max":
                    install_ui_ux_pro_max(args.project, args.agent, args.dry_run, plans.get(item_id))
                else:
                    INSTALLERS[item_id](args.project, args.agent, args.dry_run)
            if any(item_id != "codegraph" for item_id in selected):
                enable_model_invocation(plans.get("visibility", []), args.project, args.dry_run)
        print("Files and invocation policy prepared. Project initialization and host availability still require agent verification.")
        for item_id in selected:
            print(f"Pending initialization/verification: {item_id} — {ITEMS[item_id]['guide']}")
        print("Verify ignored installation artifacts and tracked project changes using docs/git-hygiene.md before declaring setup complete.")
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Setup stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
