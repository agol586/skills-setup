# Agent skills setup

This repository helps a coding agent install and configure a selected set of skills in an **existing project**. It ships an agent workflow, a small Python installer, and a guide for each built-in source. It does not vendor the upstream skills.

The local entrypoint needs Python 3. Spec Kit uses `uv` unless `specify` is already installed. Matt Pocock's skills, Archify, UI UX Pro Max, and Taste Skill use Node.js/npm; CodeGraph uses its CLI or npm for a first-time CLI install. Upstream commands access the network during installation.

## Install this workflow in your agent

Clone the repository once, then package its entry skill for the agent you use:

```bash
git clone https://github.com/agol586/skills-setup.git
cd skills-setup
python3 scripts/install-agent-skill.py --agent codex
# Or: python3 scripts/install-agent-skill.py --agent claude-code
# Or: python3 scripts/install-agent-skill.py --agent cursor
```

You can give the agent the same task directly: “Clone `https://github.com/agol586/skills-setup.git`, follow its README, and run `python3 scripts/install-agent-skill.py --agent codex` to install `agent-skill-setup` into your personal skills. Verify that its packaged catalog and setup script are present.” Replace `codex` with your agent key. This first step installs the workflow into the agent, before selecting skills for any target project.

The command installs `agent-skill-setup` under your personal skills directory: [Codex](https://developers.openai.com/codex/skills) uses `~/.agents/skills/`, [Claude Code](https://code.claude.com/docs/en/skills) uses `~/.claude/skills/`, and [Cursor](https://cursor.com/docs/skills) uses `~/.cursor/skills/`. It includes this repository's catalog, installer, and initialization guides with the entry skill, so the agent can run the workflow from another project. It leaves an existing same-name installation in place; review that copy before replacing it. If a new skill is not visible, start a new agent session.

Open the target project in your agent and give it the target path. In Codex, mention `$agent-skill-setup`; in Claude Code or Cursor, invoke `/agent-skill-setup`. For example: “Use agent-skill-setup to install the built-in skills in `/path/to/project`; show me the all-selected checklist first.” Installing this **entry skill** makes the workflow available to the agent; the six catalog sources are installed into the target project only after you make that selection.

Alternatively, give your agent this repository URL and the target project path, then ask it to follow [the setup skill](skills/agent-skill-setup/SKILL.md) from the checkout. The agent should present the catalog as a checklist with every item selected, let you deselect items, run the installer for your selection, and finish the project-specific configuration and documentation review.

For a terminal-driven run:

```bash
python3 scripts/setup.py list --project /path/to/project --agent codex
python3 scripts/setup.py inspect --project /path/to/project --agent codex
python3 scripts/setup.py install --project /path/to/project --agent codex
```

`install` prints a numbered checklist; pressing Enter installs all six. Use `--only spec-kit,codegraph` to select explicitly, `--skip archify` to deselect one, `--dry-run` to inspect commands, or `--yes` for an agent or CI session. Supported agent keys are `codex`, `claude-code`, and `cursor`. The installer runs project commands from the target root; UI UX Pro Max is generated in a temporary staging directory and missing skill files are copied into the target. It stops on the first failed upstream command and never silently marks a partial run complete. Selected skill packs are checked for missing members on each real run and restored without replacing existing files. The dry run makes no network calls, so the live upstream pack list and name-conflict check happen immediately before target writes.

For an established or already deployed project, use the [established-project workflow](docs/brownfield.md). `inspect` is read-only and reports existing Git changes, docs, and agent skills before installation. A real installation checks Matt's upstream skill names and UI UX Pro Max's bundled names before changing the target. An unrelated Matt or UI UX Pro Max companion skill with the same name stops the run; existing files are preserved when restoring a partial pack. Spec Kit checks both its shared-infrastructure and selected-integration manifests and restores missing managed files through the integration upgrade path. A checkout with Spec Kit skill remnants but no `.specify/` stops for baseline recovery instead of forcing a replacement. The installer also rejects links that would send its writes outside the target project. After installation, the agent uses CodeGraph to trace the actual architecture and key flows, writes evidence-backed logic and constraint docs, and uses Archify to validate and deliver diagrams. Existing tests and the final diff check that application behavior and project rules remain intact.

| Built-in item | Source | Project initialization |
| --- | --- | --- |
| Spec Kit | [github/spec-kit](https://github.com/github/spec-kit) | Initialize or add the chosen integration; derive constitution principles from existing docs. |
| Matt Pocock's skills | [mattpocock/skills](https://github.com/mattpocock/skills) | Run `setup-matt-pocock-skills` to configure issue tracker, labels, and domain docs. |
| CodeGraph | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | Configure the agent's MCP integration and build `.codegraph/`; trace current behavior in established projects. |
| Archify | [tt-a1i/archify](https://github.com/tt-a1i/archify) | Verify its Node-based doctor command; validate architecture and flow diagrams for established projects. |
| UI UX Pro Max | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Run `uipro init` for the selected agent; verify its search script and align recommendations with existing design docs. |
| Taste Skill | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | Install the default `design-taste-frontend` variant and infer its design dials from the existing UI. |

The item list and guide paths live in [catalog.json](catalog.json). The guides under [docs/initializers](docs/initializers) record each upstream initialization workflow and the project evidence needed to choose a branch. Keep shared configuration such as `.specify/`, `AGENTS.md`, and `docs/agents/` reviewable. Project-local skills may be committed when a checkout should work immediately, or ignored when this installer is the documented bootstrap path. Generated local CodeGraph data belongs in `.gitignore`.

Run local checks with `python3 -m unittest discover -s tests -v`.

For an end-to-end local trial, `mock-app/` is a disposable project workspace ignored by this repository's Git rules. Create or reuse it locally, run the installer against it, and inspect its own README, `docs/agents/`, and Git status. It is not included in the published installer source.
