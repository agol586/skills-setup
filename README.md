# Agent skills setup

This repository helps a coding agent install and configure a selected set of skills in an **existing project**. It ships an agent workflow, a small Python installer, and a guide for each built-in source. It does not vendor the upstream skills.

The local entrypoint needs Python 3. Spec Kit uses `uv` unless `specify` is already installed. Matt Pocock's skills, Archify, UI UX Pro Max, and Taste Skill use Node.js/npm; CodeGraph uses its CLI or npm for a first-time CLI install. Upstream commands access the network during installation.

Give your agent this repository URL and the target project path, then ask it to follow [the setup skill](skills/agent-skill-setup/SKILL.md). The agent should present the catalog as a checklist with every item selected, let you deselect items, run the installer for your selection, and finish the project-specific configuration and documentation review.

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
