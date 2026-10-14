# Skill: contract-authoring

**Tier:** invariant (contract authority, breaking classification, approval) ·
default (format, location)
**Read when:** designing a story's endpoints, writing a contract, or classifying
a change.

**References**
- Reads: `.claude/docs/design-spec.md` §12.6, §13.3, §14.2, §15 ·
  `conventions.override.md` → section `contract-authoring`
- Related: `.claude/skills/router-conventions.md`,
  `.claude/skills/error-registry.md`,
  `.claude/skills/edge-case-checklist.md`,
  `.claude/skills/plan-file-format.md`
- Calls: `.claude/scripts/contract_diff.py`
- Called by: `.claude/commands/plan-story.md`,
  `.claude/commands/change-request.md`

---

## The contract is the source of truth *(invariant)*

If code and contract disagree, that is a **bug**, not a documentation lag.

`.claude/scripts/contract_diff.py` compares the live OpenAPI output against
committed contracts. Without that check, contracts rot within a month and become
documentation nobody trusts.

During a build, any disagreement with the contract is a **stop condition** — the
implementation is wrong, or a change request is needed. Never silently resolved.

---

## Endpoints are designed as a set *(invariant)*

`/plan-story` proposes **all** endpoints for the story at once, for approval.
They are then built one at a time.

**Why as a set:** contracts within a story must be consistent with each other —
shared field names, shared filters, shared error semantics, a coherent resource
shape. Designing them one at a time produces drift inside a single feature and
gives the frontend a moving target.

**Why built one at a time:** a vertical slice is small enough to hold in
context, small enough that a bad decision costs ten minutes, and it ends in a
state where something runs.

Design is upfront. Building is incremental.

---

## What a contract contains

| Section | Notes |
|---|---|
| ID and link block | `EP-###`, parent story, requirement IDs |
| Method and path | Authoritative — the route must match |
| Permission | From the project's permission matrix |
| Path and query parameters | Types, constraints, defaults |
| Request body | Field by field: type, required, constraints, meaning |
| Success response | Status code, full shape, field meanings |
| Pagination | Sort column, cursor semantics, maximum page size |
| Error responses | **Every one, by `ERR-###`** — not a generic list |
| Idempotency | Whether a key is required, and its semantics |
| Behavioural notes | State transitions, side effects, ordering guarantees |
| Open questions | Any `Q-###` blocking this endpoint |

**Error cases are part of the contract, not an afterthought.** A contract that
lists only the happy path has deferred all the hard decisions to build time,
which is exactly where they are most expensive.

---

## Schemas are written at contract approval

The Pydantic request and response models are authored when the contract is
approved — before the build starts. They are the contract made executable.

Separate models for request and response. A response model never exposes
internal columns.

---

## Ambiguity is resolved here *(invariant)*

**This is where stopping is cheap.** By the time an endpoint is being built, the
contract plus conventions should have pre-answered almost everything.

Applied literally during the build, "stop on any ambiguity" produces stop-
fatigue and gets switched off within a week. So resolution is concentrated at
this stage, making build-time stops rare and meaningful.

**While authoring, stop and ask when:**
- A requirement does not say what happens on failure
- Two requirements imply different shapes for the same resource
- A field's meaning or format is not derivable
- A state transition's legality is unstated
- The requirement implies a rule with no error code

Questions go to `plan/questions.md` as `Q-###`. An endpoint with an unresolved
blocking question does not proceed to test authoring.

---

## Consistency rules within a story

Before proposing a set, check across it:

- Same concept, same field name, everywhere
- Same filter semantics on every list endpoint
- Same error code for the same failure across endpoints
- Resource shape identical in list and detail, or the difference is deliberate
  and stated
- Status codes follow `router-conventions` uniformly
- Pagination sort column consistent for the same resource

Inconsistency inside one story is the most common and most annoying contract
defect, because the frontend hits all of it at once.

---

## Classifying a change *(invariant)*

Every contract change is classified before approval:

**Additive** — frontend unaffected:
- New optional request field
- New response field
- New endpoint
- Relaxed validation
- New optional query parameter

**Breaking** — frontend affected:
- Field removed or renamed
- Type changed
- Validation tightened
- Status code changed
- Enum value removed
- Required field added
- Error code removed or its meaning changed
- Pagination sort column changed
- Default behaviour changed

**A breaking change always stops for approval**, with one question: version the
endpoint, or coordinate with the consumer? The answer and its reasoning go to
`plan/decisions.md` — in six months nobody remembers why `/v2` exists.

When unsure, classify as breaking. The cost of being wrong in that direction is
one conversation; the other direction is a broken frontend.

---

## Location *(default)*

`contracts/` mirrors the **API path structure**, not the story structure.

Contracts are the frontend's artifact; they will be browsed by resource, not by
your internal story numbering. The endpoint plan file links to its contract by
path.

---

## After approval

1. Schemas written
2. Story-specific error codes derived — see `error-registry`
3. `agents/test-author.md` writes tests **from the contract**, before
   implementation
4. `/build-endpoint` runs against that red suite

The build is done when the suite is green and `contract_diff.py` reports no
drift.

---

## Common violations

| Symptom | Fix |
|---|---|
| Contract lists only the happy path | Add every error case by `ERR-###` |
| Endpoints designed one at a time | Design the story's set together |
| Field named differently across two endpoints | Reconcile before approval |
| Ambiguity resolved with a sensible guess | Raise `Q-###` |
| Implementation disagrees with the contract | **Stop** — never silently fix |
| Breaking change applied without approval | **Stop** — always an approval point |
| Contract updated after the code | Contract first, always |
| Error case with no registry code | Derive the code during planning |
| Contract stored under the story folder | `contracts/`, mirroring API paths |

---

## Overrides

Check `conventions.override.md` → section `contract-authoring` for format and
location.

Contract authority, breaking classification, and the approval stop are
**invariant**.
