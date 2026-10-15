# <PROJECT NAME>

<One line: what this service does.>

---

## Conventions

Read `.claude/CLAUDE-base.md` — it holds the invariants, stop conditions, and
output rules for this project.

**Resolution order:**

1. **Invariants** in `.claude/CLAUDE-base.md` — never overridden
2. **`conventions.override.md`** (this directory) — supersedes defaults,
   sectioned by skill name; read only the section for the skill you are using
3. **`.claude/skills/*.md`** — defaults

Full reasoning: `.claude/docs/design-spec.md`. Read the section you need, never
the whole file.

---

## Where things are

| Need | Path |
|---|---|
| Project state | `plan/index.md` |
| Requirements | `plan/requirements/inventory.md` |
| Project config — roles, tenancy, choices | `plan/project-config.md` |
| Contracts | `contracts/` |
| Error registry | `plan/errors.md` |
| Open questions | `plan/questions.md` |
| Decisions | `plan/decisions.md` |
| Overrides | `conventions.override.md` |

---

## Start of session

Run `/status` to see where the project stands. Do not infer state from this
file or from conversation — state lives in `plan/`.

---

## Project-specific notes

<Anything true of this project that is not a convention: domain vocabulary,
external systems, quirks worth knowing. Keep it short — this file loads every
session.>

<Conventions do not go here. They go in `conventions.override.md`.>
