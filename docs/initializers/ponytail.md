# Ponytail initializer

Source: [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail). Official references: [Skills CLI installation](https://github.com/DietrichGebert/ponytail/blob/main/INSTALL.md#skills-cli) and [core skill](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md).

Install the upstream skill pack into the selected agent's project directory with the Skills CLI. The installer discovers the live pack, checks ownership through `skills-lock.json`, and adds only missing skills. It preserves existing instructions and stops on unrelated same-name skills; the setup workflow normalizes invocation metadata for model selection. The pack includes `ponytail` and companions for review, audit, debt, gain, and help.

This path installs skills only. Plugin hooks, persistent modes, and the Claude Code band are not configured. Keep the project's existing agent instructions; do not replace them with upstream `AGENTS.md`.

After Matt's setup, link the installed `ponytail/SKILL.md` from the project's agent guidance for coding tasks. Apply its reuse and minimal-complete-change guidance within the project's contracts and requested scope. Keep Matt's skills as the default workflow entrypoint. Use review or audit companions when the task calls for them.

Check: every discovered pack member exists under the selected agent's skills directory, the agent can invoke `ponytail`, and project guidance links to it without competing workflow entrypoints.
