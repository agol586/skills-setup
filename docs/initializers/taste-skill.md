# Taste Skill initializer

Source: [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill). Official references: [installation and variants](https://github.com/Leonxlnx/taste-skill#installing) and [default skill](https://github.com/Leonxlnx/taste-skill/blob/main/skills/taste-skill/SKILL.md).

The installer uses the `skills` CLI to install **one** upstream skill: `design-taste-frontend`, the repository's default Taste Skill variant. The source also offers specialized and image-generation variants, but this catalog entry does not install them. The default v2 variant is currently marked experimental upstream; projects that depend on v1 can select that variant directly from upstream outside this catalog.

This is a prompt-driven design skill rather than a project generator. Read the target project's README, visual/design docs, tokens, existing UI, and motion conventions. At first use, infer its three 1–10 dials—`DESIGN_VARIANCE`, `MOTION_INTENSITY`, and `VISUAL_DENSITY`—from those sources. The upstream default is 8 / 6 / 4 when no project evidence changes it. Overrides are conversational; the project does not need to edit the installed `SKILL.md` to set the dials. Preserve an established design language and record any durable choices in the project's existing design documentation, not in a second competing rule file.

When UI UX Pro Max is also selected, use the same design documentation as the baseline for both skills. A new UI brief can drive new recommendations, but existing brand and component rules remain the reference for changes to the current product.

Check: `design-taste-frontend/SKILL.md` is present in the selected agent's project skills, the agent can invoke it, and its first design read can name the project's actual visual baseline and three dials.
