---
description: Toolkit sync state — current commit, commits behind, uncommitted changes in .claude/, active overrides.
argument-hint: (none)
---

# /toolkit-status

Separate from `/status` on purpose. Different question, different cadence.

**Calls:** `.claude/scripts/check_links.py`

---

## Steps

**1. Inside `.claude/`:** current commit, current branch, fetch, count commits
behind `origin/main`.

**2. Uncommitted changes in `.claude/`** — list them by file.

**3. Read** `conventions.override.md` and list active overrides by skill
section.

**4. Run** `check_links.py` on toolkit cross-references.

---

## Report

| Section | Contents |
|---|---|
| **Toolkit commit** | SHA, date, subject |
| **Behind remote** | N commits, with subjects if any |
| **Local changes** | Files modified in `.claude/` — **flagged prominently** |
| **Active overrides** | By skill, with the recorded reason |
| **Cross-reference integrity** | Only if it fails |

---

## The state that matters

**An uncommitted change inside `.claude/` is an undecided state.** It is either:

- **Universal** → `/promote-to-toolkit` pushes it to the toolkit
- **Project-specific** → it belongs in `conventions.override.md`, not here

Left undecided, this project quietly has a private version of a skill and the
next project never gets the improvement.

Under the per-project model there is no hook blocking edits in `.claude/` —
editing there is how promotion works. **Visibility is the only safeguard**,
which is what this command is for.

See `.claude/docs/decisions.md` TD-030.

---

## When behind the remote

Report it. Do not pull automatically.

`/update-toolkit` is run **between stories, never mid-story** — a convention
changing under a half-built story produces inconsistency between endpoints.

---

## Override drift

If the same override shows up repeatedly across projects, it should stop being
an override and become a toolkit default or a project choice.

This command cannot see other projects, but it is the right place to notice
when a project has accumulated many overrides — usually a sign the toolkit is
drifting from how you actually work.

---

## Do not

- Pull, commit, or push anything — this command only reports
- Mix in project progress; that is `/status`
- Treat a local change as fine because tests pass
