# Agent skills setup

This repository provides `agent-skill-setup`, a skill for batch installing or updating selected skills in an **existing project**, making them available to the agent, completing project-specific initialization, and keeping downloaded dependencies out of Git. It ships an agent workflow, a small Python installer, and a guide for each built-in source. It does not vendor the upstream skills.

The local entrypoint needs Python 3 and the YAML dependency in `requirements.txt` (install it in your chosen Python environment). Matt Pocock's skills, Ponytail, Archify, UI UX Pro Max, and Taste Skill use Node.js/npm; CodeGraph uses its CLI or npm for a first-time CLI install. Upstream commands access the network during installation.

Matt Pocock's skills are the default project workflow entrypoint. After installation, run `setup-matt-pocock-skills` first, then use the relevant Matt skill for engineering work. Ponytail complements it with reuse, minimal complete changes, and focused reviews. Spec Kit is no longer part of the catalog; existing projects' Spec Kit files are left intact.

## Install this workflow in your agent

Clone the repository once, then package its entry skill for the agent you use:

```bash
git clone https://github.com/agol586/skills-setup.git
cd skills-setup
python3 -m pip install -r requirements.txt
python3 scripts/install-agent-skill.py --agent codex
# Or: python3 scripts/install-agent-skill.py --agent claude-code
# Or: python3 scripts/install-agent-skill.py --agent cursor
```

You can give the agent the same task directly: “Clone `https://github.com/agol586/skills-setup.git`, follow its README, and run `python3 scripts/install-agent-skill.py --agent codex` to install `agent-skill-setup` into your personal skills. Verify that its packaged catalog and setup script are present.” Replace `codex` with your agent key. This first step installs the workflow into the agent, before selecting skills for any target project.

The command installs `agent-skill-setup` under your personal skills directory: [Codex](https://developers.openai.com/codex/skills) uses `~/.agents/skills/`, [Claude Code](https://code.claude.com/docs/en/skills) uses `~/.claude/skills/`, and [Cursor](https://cursor.com/docs/skills) uses `~/.cursor/skills/`. It includes this repository's catalog, installer, and initialization guides with the entry skill, so the agent can run the workflow from another project. The packaged entry skill explicitly enables implicit invocation. It leaves an existing same-name installation in place; review that copy before replacing it. If a new skill is not visible, start a new agent session.

Open the target project in your agent and give it the target path. In Codex, mention `$agent-skill-setup`; in Claude Code or Cursor, invoke `/agent-skill-setup`. For example: “Use agent-skill-setup to install the built-in skills in `/path/to/project`; show me the all-selected checklist first.” Installing this **entry skill** makes the workflow available to the agent; the six catalog sources are installed into the target project only after you make that selection.

For upstream updates, ask the agent to use `agent-skill-setup` to update the selected catalog sources and follow [the update workflow](docs/updating.md). The `install` command repairs missing files and invocation settings; it does not replace existing skill content. The update workflow stages current upstream files, backs up the selected dependencies, replaces only that selection, and rechecks initialization.

Alternatively, give your agent this repository URL and the target project path, then ask it to follow [the setup skill](skills/agent-skill-setup/SKILL.md) from the checkout. The agent should present the catalog as a checklist with every item selected, let you deselect items, run the installer for your selection, and finish the project-specific configuration and documentation review.

For a terminal-driven run:

```bash
python3 scripts/setup.py list --project /path/to/project --agent codex
python3 scripts/setup.py inspect --project /path/to/project --agent codex
python3 scripts/setup.py install --project /path/to/project --agent codex
```

`install` prints a numbered checklist; pressing Enter installs all six. Use `--only matt-pocock-skills,ponytail` to select explicitly, `--skip archify` to deselect one, `--dry-run` to inspect commands, or `--yes` for an agent or CI session. Supported agent keys are `codex`, `claude-code`, and `cursor`. The installer runs project commands from the target root; UI UX Pro Max is generated in a temporary staging directory and missing skill files are copied into the target. It stops on the first failed upstream command and never silently marks a partial run complete. Selected skill packs are checked for missing members on each real run and restored without replacing existing files, except for the invocation policy normalization below. The dry run makes no network calls, so the live upstream pack list and name-conflict check happen immediately before target writes.

Every real installation normalizes the invocation policy of all selected skills, including already-installed pack members: it removes the top-level `disable-model-invocation` frontmatter key from `SKILL.md`, and sets `policy.allow_implicit_invocation: true` in `agents/openai.yaml` (creating the file when absent). YAML comments, other metadata, and Markdown instructions are preserved. Unselected skills are left alone; `--dry-run` only describes this step. This also applies to the packaged `agent-skill-setup` entry skill.

These settings make the skills eligible for model invocation; they do not force the model to use every skill. Codex already defaults implicit invocation to true when the field is absent. Global skill disable settings, discovery paths, and context limits can still affect availability. Check the host's skill list after installation and refresh/restart it if necessary. Git ignore rules control versioning, not invocation policy. References: [Codex skills](https://learn.chatgpt.com/docs/build-skills#optional-metadata) and [Claude Code invocation controls](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill).

For an established or already deployed project, use the [established-project workflow](docs/brownfield.md). `inspect` is read-only and reports existing Git changes, docs, and agent skills before installation. A real installation checks Matt's and Ponytail's upstream skill names and UI UX Pro Max's bundled names before changing the target. An unrelated Matt, Ponytail, or UI UX Pro Max companion skill with the same name stops the run; existing files are preserved when restoring a partial pack. The installer also rejects links that would send its writes outside the target project. After installation, the agent uses CodeGraph to trace the actual architecture and key flows, writes evidence-backed logic and constraint docs, and uses Archify to validate and deliver diagrams. Existing tests and the final diff check that application behavior and project rules remain intact.

| Built-in item | Source | Project initialization |
| --- | --- | --- |
| Matt Pocock's skills | [mattpocock/skills](https://github.com/mattpocock/skills) | Default workflow entrypoint: run `setup-matt-pocock-skills` first to configure issue tracker, labels, and domain docs. |
| Ponytail | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | Install its skill pack and connect reuse and minimal-change guidance to the Matt workflow. |
| CodeGraph | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | Configure the agent's MCP integration and build `.codegraph/`; trace current behavior in established projects. |
| Archify | [tt-a1i/archify](https://github.com/tt-a1i/archify) | Verify its Node-based doctor command; validate architecture and flow diagrams for established projects. |
| UI UX Pro Max | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Run `uipro init` for the selected agent; verify its search script and align recommendations with existing design docs. |
| Taste Skill | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | Install the default `design-taste-frontend` variant and infer its design dials from the existing UI. |

The item list and guide paths live in [catalog.json](catalog.json). The guides under [docs/initializers](docs/initializers) record each upstream initialization workflow and the project evidence needed to choose a branch. Keep shared configuration such as `AGENTS.md` and `docs/agents/` reviewable. Installed skills and bundled templates, scripts, references, and assets are local dependencies and must be ignored. The installer adds `.gitignore` rules for `.agents/skills/`, the selected agent's skills directory, `skills-lock.json` when using the Skills CLI, generated CodeGraph data, and local update backups. It writes these rules after preflight and before installation, so partial installs remain ignored, and reasserts them after any existing negation rules. Existing agent-level `.gitignore` files also receive `/skills/` so their higher-priority rules cannot reinclude installed skills. Skill roots and their parent agent directories must be real directories, including the shared `.agents/skills/` root; symlinked layouts are rejected before installation. Keep project-specific customization in tracked docs/configuration, and document the bootstrap command for a fresh checkout. Commit project source, agent/MCP configuration, docs, diagrams, and `.gitignore`; do not ignore whole agent directories or project template directories. Already tracked generated files need an explicit, reviewed `git rm --cached` to stop tracking them while retaining local copies; the installer does not modify the Git index.

The exact target-project exclusions are listed in [the Git policy](docs/git-hygiene.md):

| Ignore rule | Applies to |
| --- | --- |
| `/.agents/skills/` | Any downloaded skill selection; includes bundled templates, scripts, references, and assets |
| `/.claude/skills/` | Claude Code installations |
| `/.cursor/skills/` | Cursor installations |
| `/skills-lock.json` | Skills CLI installation state |
| `/.codegraph/` | CodeGraph local data |
| `/.skills-setup/backups/` | Prior skill payloads and installation-state backups |

A successful script run only prepares files, invocation policy, and automated tool checks. The agent must also finish every selected initializer and confirm host availability. Report each source's installed/updated, available, initialized, and ignored status, with evidence. Pending restarts or missing project preferences remain pending rather than being reported as complete.

Run local checks with `python3 -m unittest discover -s tests -v`.

For an end-to-end local trial, `mock-app/` is a disposable project workspace ignored by this repository's Git rules. Create or reuse it locally, run the installer against it, and inspect its own README, `docs/agents/`, and Git status. It is not included in the published installer source.
