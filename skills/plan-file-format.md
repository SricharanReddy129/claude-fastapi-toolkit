# Skill: plan-file-format

**Tier:** invariant — IDs, link direction, generated indexes, single-source status
**Read when:** creating or editing anything under `plan/`.

**References**
- Reads: `.claude/docs/design-spec.md` §12
- Related: `.claude/skills/requirement-decomposition.md`,
  `.claude/skills/contract-authoring.md`
- Calls: `.claude/scripts/id_allocator.py`,
  `.claude/scripts/regen_indexes.py`,
  `.claude/scripts/check_links.py`
- Called by: every planning command
- Enforced by: hook `on_plan_edit`

---

## ID scheme *(invariant)*

| Prefix | Thing |
|---|---|
| `REQ-###` | Requirement |
| `PH-#` | Phase |
| `US-###` | User story |
| `EP-###` | Endpoint |
| `DEC-###` | Decision |
| `Q-###` | Open question |
| `CR-###` | Change request |
| `ERR-###` | Error code |

**Global, not per-parent.** `US-014` is unique on its own, so any reference
resolves without context.

**Permanent and never reused.** A removed item keeps its ID with a removed
status. Reuse would silently repoint historical references.

IDs are issued by `.claude/scripts/id_allocator.py`. Never hand-assign one —
concurrent assignment produces duplicates.

---

## Links point upward only *(invariant)*

Each file declares its **parents**. Children are never hand-listed.

| File | Declares |
|---|---|
| Endpoint | parent story, requirement IDs |
| Story | parent phase, requirement IDs |
| Phase | nothing upward |
| Decision | what it affects |
| Change request | what it touched |
| Error code | originating requirement or story |

**Why:** upward links are written once at creation and stay true forever.
Downward links need updating on every addition, and eventually one update is
missed — then Claude reads a story file, sees three endpoints, and silently
works on an incomplete set.

**Hand-written links are upward and immutable. Generated links are downward and
disposable.**

---

## Generated indexes *(invariant)*

Everything under `plan/generated/` is produced by
`.claude/scripts/regen_indexes.py` by scanning upward declarations.

**Never hand-edited.** The hook regenerates after any plan edit and fails if the
committed index does not match a fresh scan.

Generated views: phase → stories · story → endpoints · requirement →
implementing stories and endpoints · open questions by target · error codes by
story.

---

## Status lives in one place *(invariant)*

| Thing | Status owner |
|---|---|
| Endpoint | its own file |
| Story | **derived** from its endpoints |
| Phase | **derived** from its stories |
| Requirement | its own entry — active, deferred, removed |

Never hand-maintain a derived status. `/status` reads real state only because
nothing is hand-maintained.

**Endpoint statuses:** planned · contracted · tests-written · building · done ·
needs-rebuild.

`needs-rebuild` is set by `/change-request` and is what stops a changed endpoint
from being counted as complete.

---

## The link block

Every plan file opens with a fixed, machine-parseable block — ID, type, parents,
status, related IDs. It is the first thing read and the only part most lookups
need.

Keep it to identifiers and status. Prose goes below it.

---

## File contents

**Endpoint** — ID · method and path · parent story · requirement IDs · status ·
contract path · related decisions, questions, error codes · notes

**Story** — ID · parent phase · requirement IDs · status · goal · points at the
generated endpoint list, never an inline one

**Phase** — ID · status · goal · entry and exit criteria

**Requirement** — ID · **verbatim source text** · source location · status ·
changelog of every CR that touched it

**Decision** — ID · date · what was decided · why · alternatives rejected ·
what it affects

**Question** — ID · what it blocks · raised date · resolution pointing at a
decision ID

Verbatim source text matters: paraphrasing a requirement loses the thing you
need when someone asks where a rule came from.

---

## Directory layout

```
plan/
├── index.md                    # phases + current position. SHORT
├── requirements/inventory.md   # all REQ entries
├── phases/PH-#.md
├── stories/US-###.md
├── endpoints/EP-###.md
├── changes/CR-###.md
├── decisions.md                # DEC entries
├── questions.md                # Q entries
├── errors.md                   # ERR registry
└── generated/                  # never hand-edited
```

Contracts live in `contracts/`, **not** here — they mirror API paths, because
they are the frontend's artifact.

---

## Context discipline *(invariant in spirit)*

**Small indexes, detailed leaves, load on demand.**

Building one endpoint reads: `plan/index.md`, that story file, that endpoint
file, its contract, any questions it names. Four or five small files.

Impact analysis reads: the requirement entry, the generated reverse index, then
only the affected files.

**Neither path ever loads the full source document or unrelated phases.**

`plan/index.md` must stay short enough to read on every command. Anything long
belongs in a leaf.

---

## Integrity check

`.claude/scripts/check_links.py` verifies:

- Every referenced ID exists
- No ID appears twice
- Every active requirement is claimed by a story, or explicitly deferred
- Every endpoint belongs to a story that belongs to a phase
- Generated indexes match a fresh scan
- Nothing marked done has unresolved questions attached
- Every toolkit cross-reference path resolves

A broken link is a failing check, not a surprise three weeks later.

---

## Writing rules

- **Never delete a requirement.** Mark it deferred or removed with a date and a
  reason. Deleting means the same argument gets relitigated with no record
- **Never renumber.** See `docs/decisions.md` TD-026
- **No secrets** — plan files are committed
- **Open questions are written to `plan/questions.md`**, not merely spoken. A
  question that exists only in a conversation does not survive compaction
- Every cross-reference is a repo-relative path or an ID, never a bare name

---

## Common violations

| Symptom | Fix |
|---|---|
| Endpoint list typed into a story file | Point at the generated index |
| Hand-assigned ID | Use `id_allocator.py` |
| Story status hand-edited | Derived from endpoints |
| Requirement paraphrased instead of quoted | Keep verbatim text |
| Requirement deleted | Mark removed with a reason |
| Generated file edited | Regenerate |
| Question raised in chat only | Write it to `plan/questions.md` |
| `plan/index.md` grown long | Move detail to leaves |

---

## No overrides

Nothing here is overridable. The format is what makes the plan machine-checkable;
a project-specific variant would break the scripts.
