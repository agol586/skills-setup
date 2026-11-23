# Keep installed dependencies out of Git

These rules apply to the **target project**, not to the authored skill source in this installer repository. Downloaded skill code, instructions, templates, scripts, reference data, bundled assets, and local backups are dependencies, not project deliverables.

| Root `.gitignore` entry | When required | Contents |
| --- | --- | --- |
| `/.agents/skills/` | Any downloaded skill source | Codex skills and the Skills CLI's shared canonical copies, including all bundled files |
| `/.claude/skills/` | Claude Code is selected | Installed skills or links for Claude Code |
| `/.cursor/skills/` | Cursor is selected | Installed skills or links for Cursor |
| `/skills-lock.json` | Matt, Ponytail, Archify, or Taste is selected | Local Skills CLI provenance/installation state |
| `/.codegraph/` | CodeGraph is selected | Local graph database and generated index data |
| `/.skills-setup/backups/` | Downloaded skills are installed or updated | Recoverable copies of prior installed dependencies and installation state |

The installer writes the rules for the current selection before target installation. Retain existing rules for other installed agents. If an agent directory has its own `.gitignore`, it also needs `/skills/` after any negation rules; a root rule alone cannot override a more-specific ignore file. Skill roots and agent directories must be real project-local directories under this installer's supported layout.

Keep `.gitignore`, `AGENTS.md`, `CLAUDE.md`, project-specific MCP settings (`.codex/config.toml`, `.cursor/mcp.json`, `.mcp.json`), `docs/agents/`, architecture/flow docs and diagrams, design decisions, source code, and project-authored templates reviewable. Do not ignore `.agents/`, `.claude/`, `.cursor/`, `.codex/`, `docs/`, or all `templates/` wholesale. If a selected upstream introduces scaffolding outside the listed paths, inspect it and add only the exact generated dependency paths; preserve project-specific output.

Before calling the task complete:

1. Run `git check-ignore -v --no-index -- <actual-installed-files>` from the target project against representative manifests, bundled templates/assets, lock files, index files, and backup files. Confirm project-specific files are not hidden by the added rules. If nested ignore files defeat a rule, repair the rule at the relevant level and check again.
2. Run `git ls-files -- <installed-dependency-paths>` to identify already tracked installation artifacts. Ignore rules do not untrack them. Inspect the exact list, then use `git rm --cached -- <reviewed-files>` (or `-r` for a directory consisting entirely of installed dependencies), retaining the local copies. Do not use `-f` to discard staged edits; reconcile those edits first. Move durable project-specific customization into the existing tracked docs/configuration before untracking a mixed directory.
3. Review `git diff --cached`, `git diff`, and `git status --short --untracked-files=all`. Expected changes are project configuration/docs, ignore rules, and any intentional index removals. No installed dependency files should be staged for addition or modification.

Record the selected sources and bootstrap/update commands in existing project docs. Retain the ignored local lock file for provenance checks; omitting it from commits does not mean deleting it from the developer's machine.
