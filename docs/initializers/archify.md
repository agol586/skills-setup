# Archify initializer

Source: [tt-a1i/archify](https://github.com/tt-a1i/archify). Official references: [quick start](https://github.com/tt-a1i/archify#quick-start) and [authoring cookbook](https://github.com/tt-a1i/archify/blob/main/docs/authoring-cookbook.md).

The installer adds the `archify` skill to the selected agent's project skill directory. Current Archify packages include standalone validation; Node.js 18+ is needed to run its CLI, but a separate `npm install` in the skill folder is not required. Run `node bin/archify.mjs doctor` from the installed skill's root. The installer does this automatically when it can locate the command.

Read the project's README and docs to identify where intentional architecture diagrams or their typed sources belong. For an established project, generate the [current-system diagrams](../brownfield.md) from CodeGraph-backed findings. Put each typed JSON source and delivered HTML alongside related project documentation, following the project's existing convention. For a new or empty project, installation alone does not require a diagram.

Check: the selected agent can see the Archify skill, `doctor` passes, and diagram location is consistent with the project's docs layout. For an established project, validate and deliver the architecture diagram and any critical-flow diagrams, and link them from its architecture overview.
