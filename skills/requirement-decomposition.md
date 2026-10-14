# Skill: requirement-decomposition

**Tier:** invariant (two passes, verbatim text, permanent IDs, no silent
resolution) · default (phase and story heuristics)
**Read when:** running `/ingest-requirements`, `/plan-phases`, or
`/new-requirement`.

**References**
- Reads: `.claude/docs/design-spec.md` §13.2, §14 ·
  `conventions.override.md` → section `requirement-decomposition`
- Related: `.claude/skills/plan-file-format.md`,
  `.claude/skills/contract-authoring.md`,
  `.claude/skills/error-registry.md`
- Writes: `plan/requirements/inventory.md`, `plan/phases/`, `plan/stories/`,
  `plan/questions.md`
- Used by: `agents/requirements-analyst.md`

---

## The input

A single document mixing requirements, SRS content, notes, specs, and technical
requirements. **This is the normal case**, not a problem to complain about.

The job is to turn it into something traceable without losing the link back to
the original wording.

---

## Pass one — inventory *(invariant)*

Extract **every atomic statement** and give it a permanent `REQ-###`:

- Functional requirements
- Business rules
- Non-functional constraints
- Explicit out-of-scope notes — these are requirements too, and the most
  commonly lost
- Technical constraints and integrations

**Each entry keeps the verbatim source text** plus its location in the document.
Paraphrasing loses exactly the thing you need when someone asks where a rule
came from.

**One statement per entry.** A sentence containing three rules becomes three
entries. Rules that travel together in the document often get implemented in
different places.

### Ambiguity goes to the register, never resolved silently *(invariant)*

Anything vague, contradictory, or incomplete becomes a `Q-###` in
`plan/questions.md` — **not** a reasonable assumption written as a requirement.

This is where the "stop and ask" rule earns its keep: ambiguity is cheapest to
resolve here, before anything is built on top of it.

Flag: unquantified terms ("fast", "secure", "large"), undefined roles or
entities, rules with no stated failure behaviour, conflicting statements,
implied features never described.

### The review property

The output is a flat numbered list that **covers the document** — reviewable
side by side with the source so gaps are visible.

A reviewer should be able to read the source and the inventory together and spot
anything missing. That property is the point of pass one.

---

## Project config extraction

Also from the document, proposed as **findings** for approval — not asked as
questions before reading:

| Finding | Source signal |
|---|---|
| Database engine | Stated, or inferred from context |
| Role names | Who does what in the document |
| Permission matrix | Role × operation, assembled from the rules |
| Tenant-scoped entities | What belongs to a customer |
| Soft-delete scope | Where history or recovery is implied |
| Idempotency scope | Financial or externally-triggered operations |
| Sub-folder organisation | Feature-shaped or resource-shaped document |

Each finding cites the `REQ-###` that supports it. A finding with no supporting
requirement is a question, not a finding.

---

## Global error codes

Derived at this stage: auth failures, tenancy violations, validation,
pagination, idempotency conflicts. Written to `plan/errors.md`.

See `.claude/skills/error-registry.md`.

---

## Pass two — grouping *(invariant)*

Requirement IDs are grouped into **phases**, then into **stories**.

**Every story cites the requirement IDs it satisfies.**
**Every requirement lands in a story or is explicitly marked deferred or
out-of-scope.** Nothing silently disappears — `check_links.py` enforces this.

### Phase heuristics *(default)*

- Phase 0 is always auth — see `auth-module-build`
- A phase delivers something coherent and demonstrable
- Dependencies point backward: a phase does not depend on a later one
- Prefer fewer, larger phases over many small ones — phases are planning units,
  not sprints
- Foundational data models land in the phase of the first story that needs them

### Story heuristics *(default)*

- A story is one feature or capability, from a user's point of view
- Sized so its endpoints can be designed as a consistent set — see
  `contract-authoring`
- A story that needs more than roughly six endpoints is usually two stories
- A story with one endpoint is fine
- Cross-cutting concerns (audit, pagination) are conventions, not stories

Endpoints are **not** decided here. They are designed at `/plan-story`.

---

## New requirements

`/new-requirement` — the light path, when nothing existing is affected:

1. New `REQ-###` in the inventory
2. User assigns it to a phase
3. New story, or extends an existing one
4. Story-specific error codes derived

**No impact analysis** — it would find nothing.

**If the new requirement contradicts an existing one**, it is not new. Stop and
route to `/change-request`.

---

## Changed requirements

Handled by `/change-request`, not here. See
`.claude/docs/design-spec.md` §14.2.

---

## Requirement IDs are permanent *(invariant)*

**Decomposition runs once.** A revised source document is **diffed against the
inventory** — what is new, what changed, what disappeared — reviewed, and
applied as change requests.

Re-running decomposition renumbers requirements and breaks every trace link in
the project.

Phase re-planning is separate and rare: `/plan-phases` can regroup existing
stories without touching requirement IDs or contracts.

---

## Scope removal *(invariant)*

Requirements are marked **deferred** or **removed** with a date and a reason.
**Never deleted.**

Deleting means the same argument gets relitigated in three months with no record
of how it was settled.

Endpoints already built against a removed requirement get an explicit decision:
leave, deprecate, or remove.

---

## Context discipline

The full source document is read by `agents/requirements-analyst.md` in its own
context, which returns the structured inventory.

**The main session never loads the whole document.** It reads the inventory.

---

## Common violations

| Symptom | Fix |
|---|---|
| Requirement paraphrased | Keep verbatim text plus location |
| Three rules in one entry | Split them |
| Ambiguity resolved with a sensible assumption | Raise `Q-###` instead |
| Out-of-scope notes dropped | They are requirements too |
| Requirement in no story and not marked deferred | Assign or defer explicitly |
| Finding with no supporting `REQ-###` | It is a question |
| Endpoints designed during decomposition | That is `/plan-story` |
| Decomposition re-run on a revised document | Diff and apply as change requests |
| Requirement deleted | Mark removed with a reason |

---

## Overrides

Check `conventions.override.md` → section `requirement-decomposition` for phase
and story heuristics.

Two passes, verbatim text, permanent IDs, and no silent ambiguity resolution are
**invariant**.
