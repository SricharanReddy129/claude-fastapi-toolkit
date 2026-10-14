# Skill: edge-case-checklist

**Tier:** invariant (the walk and the record) · default (the categories)
**Read when:** authoring tests for any endpoint, or verifying a story.

**References**
- Reads: `.claude/docs/design-spec.md` §10.7 ·
  `conventions.override.md` → section `edge-case-checklist`
- Related: `.claude/skills/testing-strategy.md`,
  `.claude/skills/contract-authoring.md`,
  `.claude/skills/error-registry.md`
- Used by: `agents/test-author.md`, `.claude/commands/verify-story.md`

---

## How to use this

Walk **every category** for **every endpoint**. For each one, either write the
test or record it as N/A with a one-line reason in the endpoint's test file
header.

Most endpoints mark half of these N/A. **That is expected.** The value is not
coverage for its own sake — it is that the question was asked and the answer is
auditable.

A category silently skipped is indistinguishable from a category forgotten,
which is the whole problem this file solves.

Fewer tests only works if the ones that remain are chosen deliberately.

---

## Auth and tenancy

| Case | Notes |
|---|---|
| Missing token | 401 |
| Malformed token | 401 |
| Expired token | 401 — happens constantly with 15-minute tokens, test it properly |
| Valid token, disallowed role | 403 |
| **Valid token, another tenant's record** | **404 — mandatory, no exceptions** |
| Wrong token type (`typ`) | 401 |

The cross-tenant case is the test that catches a missing DAL filter. It is never
N/A on an endpoint touching tenant data.

---

## Resource state

| Case | Notes |
|---|---|
| Not found | 404 |
| Soft-deleted record | 404 or 410 — per project choice |
| Exists but in a state this operation forbids | Registry conflict error |
| Already processed | Illegal transition, or idempotent replay |

---

## Validation

| Case | Notes |
|---|---|
| Required field missing | |
| Wrong type | |
| Empty string vs explicit null | Different meanings — test both |
| Oversized string | Past the declared maximum |
| Number out of range | Both ends |
| Invalid enum value | |
| Unexpected extra fields | Rejected or ignored — the contract decides |
| Unicode and emoji | Especially in names and free text |
| Whitespace-only | Should usually fail where empty fails |

---

## Numeric and money

| Case | Notes |
|---|---|
| Zero | |
| Negative | Where it should be impossible |
| Precision and rounding | Half-up vs banker's — the contract decides |
| Very large values | Past realistic bounds |

---

## Dates and time

| Case | Notes |
|---|---|
| End before start | |
| Past or future constraint violated | |
| Timezone handling | |
| Naive vs aware datetime | A common silent bug |

---

## State transitions

| Case | Notes |
|---|---|
| Each illegal transition | Each has its own error code |
| Acting on an already-processed record | |
| Transition by a role not permitted to make it | Record-level, enforced in the service |

---

## Idempotency *(where the endpoint requires a key)*

| Case | Notes |
|---|---|
| Same key, same request | Returns the stored response |
| Same key, different request | 409 |
| Concurrent duplicates | Only one executes |
| Key from another tenant | Never matches |

---

## Concurrency

| Case | Notes |
|---|---|
| Double submit | |
| Stale update — someone else wrote first | |

Note the limitation in `testing-strategy` — rollback isolation cannot test
genuinely concurrent commits. Test what is testable; record the rest.

---

## Collections and pagination

| Case | Notes |
|---|---|
| Empty collection | |
| Exactly one item | Off-by-one boundary |
| Maximum page size | |
| Page size above the maximum | Rejected or clamped — per project |
| Page past the end | Empty page, no cursor |
| Invalid sort field | |
| Invalid or unparseable cursor | Error, never silently page one |
| Cursor issued under a different sort order | Error |

---

## Referential integrity

| Case | Notes |
|---|---|
| Foreign key that does not exist | |
| Foreign key in another tenant | 404, not a FK error |
| Unique constraint violation | |
| Unique value re-used after soft delete | Depends on the partial-index choice |
| Delete with children | Blocked, cascaded, or soft — the contract decides |

---

## PATCH semantics

| Case | Notes |
|---|---|
| Field omitted vs explicitly null | Must mean different things |
| Empty body | |
| Field present but unchanged | |
| Read-only field included | Rejected or ignored — the contract decides |

---

## Recording the walk

At the top of each endpoint's test file, record every category as **covered** or
**N/A with a reason**.

`/verify-story` checks that the record exists and is complete. A missing record
fails verification — the story is not done.

---

## When a case has no error code

If walking this checklist surfaces a failure mode with no entry in the error
registry, that is a **planning gap**, not something to improvise.

Stop, raise it as an open question, and either add the code via the planning
flow or confirm the case is genuinely out of scope. Do not invent a code inline.

---

## Overrides

Check `conventions.override.md` → section `edge-case-checklist`. A project may
add categories — domain-specific ones usually belong here.

**Removing a category is not an override.** Mark individual cases N/A per
endpoint instead; that keeps the record honest.
