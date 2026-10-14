---
description: Turn the source document into a numbered requirement inventory, a project config proposal, and the global error codes.
argument-hint: <path-to-requirements-document>
---

# /ingest-requirements

**Runs once per project.** Everything downstream traces back to what this
produces.

**Loads**
- `.claude/skills/requirement-decomposition.md`
- `.claude/skills/plan-file-format.md`
- `.claude/skills/error-registry.md`

**Delegates to:** `.claude/agents/requirements-analyst.md`
**Calls:** `.claude/scripts/id_allocator.py`, `.claude/scripts/check_links.py`

---

## Input

`$ARGUMENTS` — path to the source document. A single blob mixing requirements,
SRS content, notes, specs, and technical requirements is the normal case.

If no path is given, ask for one. Do not proceed on a description.

---

## Steps

**1. Pass one — inventory (delegated).**
Hand the document to `requirements-analyst`. The main session must **not** load
the whole document; it works from the returned inventory.

Returns: every atomic statement as a `REQ-###` entry with **verbatim source
text** and location, plus ambiguities as `Q-###` candidates.

**2. Write the inventory** to `plan/requirements/inventory.md`.
Write questions to `plan/questions.md`.

**3. Present the ambiguity register.**
Show every `Q-###`. These are resolved by the user, not by assumption. Anything
blocking cannot proceed to phases.

**4. Propose project config as findings.**
Each finding cites the `REQ-###` supporting it. A finding with no supporting
requirement is a question, not a finding.

Database engine · role names · permission matrix · tenant-scoped entities ·
soft-delete scope · idempotency scope · sub-folder organisation.

**Stop for approval.** Write the approved set to `plan/project-config.md`.

**5. Derive global error codes** — auth, tenancy, validation, pagination,
idempotency. Write to `plan/errors.md`.

**6. Initialise `plan/index.md`** with project name and status. Keep it short.

**7. Run `check_links.py`.** Report the result.

---

## Output

| File | Contents |
|---|---|
| `plan/requirements/inventory.md` | All `REQ-###` entries |
| `plan/questions.md` | All `Q-###` |
| `plan/project-config.md` | Approved findings |
| `plan/errors.md` | Global error codes |
| `plan/index.md` | Initialised |

---

## Stop conditions

- No document path given
- Document unreadable or clearly truncated
- Any finding lacks a supporting requirement
- Before writing `plan/project-config.md` — always an approval point

---

## Do not

- Load the full document into the main context
- Resolve an ambiguity with a reasonable assumption — raise `Q-###`
- Paraphrase a requirement — keep verbatim text
- Drop out-of-scope notes — they are requirements too
- Design endpoints — that is `/plan-story`
- Re-run this on a revised document — diff and use `/change-request`

---

## Next

`/plan-phases` once blocking questions are resolved. Foundation and Phase 0 auth
are built before story work begins.
