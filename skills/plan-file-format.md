# Skill: plan-file-format

**Tier:** invariant — IDs, link direction, generated indexes, single-source
status, frontmatter shape
**Read when:** creating or editing anything under `plan/`.

**References**
- Reads: `.claude/docs/design-spec.md` §12
- Related: `.claude/skills/requirement-decomposition.md`,
  `.claude/skills/contract-authoring.md`
- Calls: `.claude/scripts/id_allocator.py`,
  `.claude/scripts/regen_indexes.py`, `.claude/scripts/check_links.py`
- Templates: `plan/phases/_template.md`, `plan/stories/_template.md`,
  `plan/endpoints/_template.md`, `plan/changes/_template.md`
- Enforced by: hook `on_plan_edit`

---

## Frontmatter *(invariant)*

Every leaf plan file opens with YAML frontmatter between `---` markers. This is
the machine-readable part; prose goes below it.

**The format is deliberately flat**, because the scripts that parse it are
stdlib-only and cannot import a YAML library:

- One `key: value` per line
- Lists are bracketed and comma-separated: `[REQ-001, REQ-002]`
- Empty lists are `[]`
- **No nesting, no multi-line values, no anchors, no quoting needed**
- Values containing a comma must not be used in a list field

A file whose frontmatter does not parse fails `check_links.py`. If something
does not fit the flat format, it belongs in the prose below, not in a key.

Start from the templates rather than writing frontmatter by hand.

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

Each file declares its **parents** in frontmatter. Children are never listed.

| File | Upward keys |
|---|---|
| Endpoint | `story`, `requirements` |
| Story | `phase`, `requirements` |
| Phase | none |
| Change request | `requirement`, plus what it touched |

**Why:** upward links are written once at creation and stay true forever.
Downward links need updating on every addition, and eventually one update is
missed — then Claude reads a story file, sees three endpoints, and silently
works on an incomplete set.

**Hand-written links are upward and immutable. Generated links are downward and
disposable.**

---

## Generated indexes *(invariant)*

Everything in `plan/generated/` is produced by
`.claude/scripts/regen_indexes.py` by scanning frontmatter.

**Never hand-edited.** The hook regenerates after any plan edit and fails if the
committed index does not match a fresh scan.

Generated views: phase → stories · story → endpoints · requirement →
implementing stories and endpoints · open questions by target · error codes by
story.

---

## Status lives in one place *(invariant)*

| Thing | Status owner |
|---|---|
| Endpoint | its own frontmatter |
| Story | **derived** from its endpoints |
| Phase | **derived** from its stories |
| Requirement | its own entry — active, deferred, removed |

Never hand-edit a derived status. `/status` reads real state only because
nothing is hand-maintained.

**Endpoint statuses:** `planned` · `contracted` · `tests-written` · `building` ·
`done` · `needs-rebuild`.

`needs-rebuild` is set by `/change-request` and is what stops a changed endpoint
from counting as complete.

---

## Frontmatter keys by file type

**Phase** — `id`, `type`, `status`, `name`

**Story** — `id`, `type`, `phase`, `requirements`, `status`, `questions`, `name`

**Endpoint** — `id`, `type`, `story`, `requirements`, `status`, `method`,
`path`, `contract`, `permission`, `tenant_scoped`, `idempotency_key`, `errors`,
`decisions`, `questions`

**Change request** — `id`, `type`, `date`, `requirement`, `status`,
`classification`, `stories`, `endpoints`, `contracts`, `decisions`

Keys are never omitted. An empty list is `[]`; an unknown value is the
placeholder from the template.

---

## Flat files

`plan/requirements/inventory.md`, `plan/questions.md`, `plan/decisions.md`, and
`plan/errors.md` hold many entries in one file and use **heading-delimited
entries**, not frontmatter. Each entry starts with `### <ID>` and follows the
format documented at the top of its file.

---

## Directory layout

```
plan/
├── index.md                    # phases + current position. SHORT
├── project-config.md           # roles, tenancy, project choices
├── requirements/inventory.md
├── phases/PH-#.md
├── stories/US-###.md
├── endpoints/EP-###.md
├── changes/CR-###.md
├── decisions.md
├── questions.md
├── errors.md
└── generated/                  # never hand-edited
```

Contracts live in `contracts/`, **not** here — they mirror API paths, because
they are the frontend's artifact.

---

## Context discipline

**Small indexes, detailed leaves, load on demand.**

Building one endpoint reads: `plan/index.md`, that story file, that endpoint
file, its contract, any questions it names. Four or five small files.

Impact analysis reads: the requirement entry, the generated reverse index, then
only the affected files.

**Neither path ever loads the full source document or unrelated phases.**

`plan/index.md` must stay short enough to read on every command.

---

## Integrity check

`.claude/scripts/check_links.py` verifies:

- Frontmatter parses in every leaf file
- Every required key is present
- Every referenced ID exists
- No ID appears twice
- Every active requirement is claimed by a story, or explicitly deferred
- Every endpoint belongs to a story that belongs to a phase
- Generated indexes match a fresh scan
- Nothing marked `done` has unresolved questions attached
- Every toolkit cross-reference path resolves

---

## Writing rules

- **Never delete a requirement.** Mark deferred or removed with a date and
  reason
- **Never renumber.** See `docs/decisions.md` TD-026
- **No secrets** — plan files are committed
- **Open questions go to `plan/questions.md`**, not merely spoken. A question
  that exists only in conversation does not survive compaction
- Every cross-reference is a repo-relative path or an ID, never a bare name

---

## Common violations

| Symptom | Fix |
|---|---|
| Endpoint list typed into a story file | Point at the generated index |
| Hand-assigned ID | Use `id_allocator.py` |
| Story status hand-edited | Derived from endpoints |
| Nested or multi-line frontmatter | Flatten it, or move to prose |
| Missing frontmatter key | Every key is always present; `[]` for empty |
| Requirement paraphrased | Keep verbatim text |
| Requirement deleted | Mark removed with a reason |
| Generated file edited | Regenerate |
| Question raised in chat only | Write it to `plan/questions.md` |
| `plan/index.md` grown long | Move detail to leaves |

---

## No overrides

Nothing here is overridable. The format is what makes the plan
machine-checkable; a project-specific variant would break the scripts.
