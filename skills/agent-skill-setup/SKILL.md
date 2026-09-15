---
name: agent-skill-setup
description: Install this repository's built-in agent skill catalog into an existing project, initialize each selected item from project evidence, and reconcile agent docs and gitignore.
---

# Set up a target project

Use this skill when an agent receives this repository as the source for setting up another project. The built-in list comes from [`catalog.json`](../../catalog.json); it is a list of **sources**, so Matt Pocock's source and UI UX Pro Max install packs rather than one skill each. Taste Skill installs its default `design-taste-frontend` variant.

1. Resolve the target project root and coding agent (`codex`, `claude-code`, or `cursor`). Run `python3 scripts/setup.py inspect --project <root> --agent <key>` and read the project's README, existing `AGENTS.md`/`CLAUDE.md`, relevant `docs/`, git remote, existing skill directories, `.specify/`, and `.gitignore`. If `.codegraph/` already exists, use CodeGraph to locate code before text search. For a project with application code or released behavior, follow [the established-project path](../../docs/brownfield.md), including its reviewable baseline. Finish when you can name the current documentation layout, pre-existing changes, and which selected items are already present.
2. Show the catalog items as a checkbox list, **all checked by default**, with their current status from `python3 scripts/setup.py list --project <root> --agent <key>`. Ask which boxes to clear only when the user's selection is unknown. A direct request to install all means every catalog item remains selected. Finish when the selected IDs are explicit.
3. Run `python3 scripts/setup.py install --project <root> --agent <key> --only <comma-separated-ids> --yes --dry-run` and inspect the target paths it may modify. Then run the same command without `--dry-run`. The script stops on upstream failures; resolve the failure and rerun selected items. Read the guide for **each selected item** and complete its document-sensitive steps. Finish when every selected item passes the guide's check, including the prompt-driven Matt setup.
4. Reconcile project documentation: use the existing README/docs convention for a single setup entrypoint, keep upstream-specific detail in the selected guides or existing project docs, preserve existing agent instructions, and link any new `docs/agents/` configuration from the project's agent instruction file. For an established project, complete the CodeGraph-backed architecture, critical-flow, constraint, and Archify diagram deliverables in [the established-project path](../../docs/brownfield.md) before deriving new agent rules. Review `.gitignore` so local CodeGraph index data stays out of Git. For project-local skill files, choose a deliberate policy: commit them when a checkout must work immediately; ignore them only when a documented bootstrap command can restore **every** selected item, including Spec Kit skills and UI UX Pro Max companions. Keep shared specs and agent configuration reviewable. Finish when the project docs describe current behavior, what was installed, how to use it, and where its configuration lives; `git status` shows only intended source/config changes.

The installer automates commands, not the decisions that depend on the target project's documentation. Read the relevant guide only after the item is selected:

- [Spec Kit](../../docs/initializers/spec-kit.md): existing `.specify/`, integration, and constitution.
- [Matt Pocock's skills](../../docs/initializers/matt-pocock-skills.md): issue tracker, triage labels, and domain docs.
- [CodeGraph](../../docs/initializers/codegraph.md): local agent MCP configuration and index verification.
- [Archify](../../docs/initializers/archify.md): doctor check and diagram location.
- [UI UX Pro Max](../../docs/initializers/ui-ux-pro-max.md): CLI initialization, search check, and existing design system.
- [Taste Skill](../../docs/initializers/taste-skill.md): default variant and project-derived design dials.
