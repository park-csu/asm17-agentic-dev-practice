# CLAUDE.md

@AGENTS.md

## Skill synchronization

This project follows the official Agent Skills `SKILL.md` specification.

When updating local skills for Claude:

1. Create a local `.claude/skills/` directory if it does not exist.
2. Copy the contents of `.agents/skills/` into `.claude/skills/`.
3. Notify the user to reload Claude so the skill changes are applied.

Rules:

- Do not edit files directly under `.claude/skills/`.
- Do not modify `.gitignore` as part of skill synchronization.
