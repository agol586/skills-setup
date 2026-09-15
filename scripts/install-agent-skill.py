#!/usr/bin/env python3
"""Install this repository's entry skill as a self-contained personal skill."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "agent-skill-setup"
DEFAULT_SKILLS_DIR = {
    "codex": Path.home() / ".agents" / "skills",
    "claude-code": Path.home() / ".claude" / "skills",
    "cursor": Path.home() / ".cursor" / "skills",
}


def install(agent: str, skills_dir: Path) -> Path:
    source_skill = ROOT / "skills" / SKILL_NAME / "SKILL.md"
    source_root = ROOT
    destination = skills_dir.expanduser().resolve() / SKILL_NAME
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Skill already exists: {destination}. Review the installed copy before replacing it.")

    original = source_skill.read_text(encoding="utf-8")
    parts = original.split("---", 2)
    if len(parts) < 3 or "name: agent-skill-setup" not in parts[1] or "description:" not in parts[1]:
        raise ValueError(f"Invalid skill frontmatter: {source_skill}")
    wrapper = (
        f"---{parts[1]}---\n\n"
        "# Set up a target project\n\n"
        "Read the [full workflow](source/skills/agent-skill-setup/WORKFLOW.md) before acting. "
        "The catalog, initializer guides, and installer are packaged in `source/` beside this file. "
        "Resolve this skill's directory and run `source/scripts/setup.py` by absolute path; "
        "resolve relative script paths in the workflow against `source/`. "
        "The installer itself executes project commands from the target root. "
        "Follow workflow links from the packaged `source/` tree.\n"
    )

    skills_dir = skills_dir.expanduser().resolve()
    skills_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".agent-skill-setup-", dir=skills_dir) as temporary:
        staged = Path(temporary) / SKILL_NAME
        packaged = staged / "source"
        (packaged / "scripts").mkdir(parents=True)
        (packaged / "skills" / SKILL_NAME).mkdir(parents=True)
        shutil.copy2(source_root / "catalog.json", packaged / "catalog.json")
        shutil.copy2(source_root / "scripts" / "setup.py", packaged / "scripts" / "setup.py")
        shutil.copy2(source_skill, packaged / "skills" / SKILL_NAME / "WORKFLOW.md")
        shutil.copytree(source_root / "docs", packaged / "docs")
        (staged / "SKILL.md").write_text(wrapper, encoding="utf-8")
        staged.rename(destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=DEFAULT_SKILLS_DIR, required=True)
    parser.add_argument("--skills-dir", type=Path, help="Override the agent's personal skills directory")
    args = parser.parse_args()
    try:
        destination = install(args.agent, args.skills_dir or DEFAULT_SKILLS_DIR[args.agent])
    except (FileExistsError, OSError, ValueError) as exc:
        parser.exit(1, f"Skill installation stopped: {exc}\n")
    print(f"Installed {SKILL_NAME} for {args.agent}: {destination}")
    print("Open a new agent session if the skill does not appear immediately, then invoke agent-skill-setup with a target project path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
