---
description: Push a universal improvement from .claude/ to the toolkit repo.
argument-hint: [file path] (default: all changes in .claude/)
---

# /promote-to-toolkit

Commits and pushes from inside `.claude/` straight to the toolkit's `main`.

The project is immediately on the promoted commit, because it **is** that
commit. No copy-down step, no drift window.

**Calls:** `.claude/scripts/check_links.py`

---

## The question this command exists to force

For every change in `.claude/`: **universal, or project-specific?**

| Answer | Destination |
|---|---|
| **Universal** — true for every future project | Promote. This command |
| **Project-specific** — true only here | `conventions.override.md`. **Not this command** |

Promoting a project-specific preference makes it the default for every future
project. That is the mistake this command is designed to catch.

---

## Steps

1. **Show the diff** in `.claude/`, file by file
2. **For each file, ask** universal or project-specific — unless the answer is
   obvious from the change itself (a typo fix, a broken path)
3. **Project-specific changes:** move the intent into
   `conventions.override.md` under the right skill section, with a reason and a
   date, then **revert the `.claude/` file**
4. **Run `check_links.py`** — pushing a skill that references a script you did
   not also change breaks the toolkit for every future project
5. **Stop for confirmation** of what will be pushed
6. Commit inside `.claude/` with a message describing the improvement, push to
   `main`
7. Report the new commit

---

## Before promoting, check

- **Is it project-agnostic?** No project names, no domain-specific entity names,
  no tenant-specific rules
- **Does it reference anything new?** A new script, a new skill — promote those
  together
- **Does it contradict `docs/design-spec.md`?** Then the spec needs amending in
  the same commit, with a row in its amendment log
- **Does it weaken an invariant?** Stop. Invariants change only as a deliberate
  design decision, with `docs/decisions.md` updated

---

## Straight to main

No review branch — single user, and ceremony that is not needed gets skipped
anyway.

The accepted risk is that a half-formed idea becomes the template for every
future project immediately. `check_links.py` before push is the only guardrail.
Reasoning: `.claude/docs/decisions.md` TD-031.

---

## Do not

- Promote without deciding universal vs project-specific for each change
- Promote a change that references a file you did not include
- Promote a weakened invariant without amending `docs/decisions.md`
- Promote secrets, project names, or domain entities
- Push if `check_links.py` fails

---

## After

Other projects pick it up with `/update-toolkit`, between stories.

If this change should have been a default rather than an override in several
projects, note it — that pattern is the best signal for what the toolkit should
become.
