---
description: Pull toolkit improvements into this project. Between stories only.
argument-hint: (none)
---

# /update-toolkit

Pulls the toolkit repo inside `.claude/`.

**Calls:** `.claude/scripts/check_links.py`

---

## Preconditions

**1. Not mid-story.**
If a story has endpoints in `building` or `tests-written`, **stop**. A
convention changing under a half-built story produces endpoints built to
different rules within one feature.

Finish or revert the story first.

**2. No uncommitted changes in `.claude/`.**
If any exist, stop and ask: promote them (`/promote-to-toolkit`), move them to
`conventions.override.md`, or discard them.

A pull over uncommitted changes either conflicts or silently loses work.

---

## Steps

1. Fetch inside `.claude/` and show what is incoming — commit subjects, files
   changed
2. **Stop for confirmation**
3. Pull
4. Run `check_links.py` — a pulled skill referencing a script that did not come
   with it is broken
5. Re-read `conventions.override.md` and report any override whose skill section
   changed upstream

---

## Report

- Commits pulled
- Skills, commands, hooks, or scripts changed
- **Overrides now possibly stale** — an override written against an old default
  may no longer make sense
- Cross-reference integrity result

---

## Stale overrides

The quiet failure mode. An override says "offset pagination instead of cursor,
because X". The toolkit then changes how pagination works entirely, and the
override now describes a choice that no longer exists.

Nothing can detect this automatically. The command flags which override sections
had upstream changes so you can look.

---

## Do not

- Pull mid-story
- Pull over uncommitted `.claude/` changes
- Resolve a conflict by discarding local work without asking
- Touch `conventions.override.md` — it belongs to the project, not the toolkit
- Rebuild or re-verify anything; pulling does not invalidate completed work

---

## After

If a convention changed in a way that affects completed endpoints, that is a
judgment call — not an automatic rebuild. Decide deliberately and log a
`DEC-###` if you act on it.
