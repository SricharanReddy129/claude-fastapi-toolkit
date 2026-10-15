---
endpoint: EP-000
method: GET
path: /api/v1/<resource>
status_success: 200
status_errors: [401, 403, 404]
permission: <permission-name>
tenant_scoped: true
idempotency_key: false
pagination: none
errors: []
requirements: [REQ-000]
---

# GET /api/v1/&lt;resource&gt;

**Purpose:** <one line — what a caller uses this for>

---

## Request

### Path parameters

| Name | Type | Constraints | Meaning |
|---|---|---|---|
| | | | |

### Query parameters

| Name | Type | Required | Default | Constraints | Meaning |
|---|---|---|---|---|---|
| | | | | | |

### Body

| Field | Type | Required | Constraints | Meaning |
|---|---|---|---|---|
| | | | | |

<!-- Omitted vs explicitly null must mean different things on PATCH. State which. -->

---

## Success response

**Status:** 200

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| | | | |

### Pagination

<!-- Delete this section when pagination: none -->

**Sort column:** <must be immutable — a mutable column silently skips or
duplicates rows between pages>

**Cursor:** signed, opaque. Encodes the sort value plus the ID as tiebreaker.

**Page size:** default <n>, maximum <n>. Above maximum: reject | clamp.

---

## Error responses

Every failure this endpoint can produce. **A contract listing only the happy
path has deferred the hard decisions to build time.**

| Status | Error code | When |
|---|---|---|
| 401 | ERR-### | No token, expired, malformed |
| 403 | ERR-### | Valid token, role not permitted |
| 404 | ERR-### | Not found, **or belongs to another tenant** |

<!-- Cross-tenant is 404, never 403 — a 403 confirms the record exists. -->

---

## Behaviour

**State transitions:** <which states this may act on, which it may move to>

**Side effects:** <what else changes, what is emitted>

**Ordering guarantees:** <if any>

**Idempotency:** <delete when idempotency_key: false>
Same key + same request returns the stored response. Same key + different
request is a 409. The key is captured before processing.

---

## Open questions

<!-- Q-### blocking this endpoint. An endpoint with a blocking question does
     not proceed to test authoring. Delete this section when empty. -->

---

<!--
FRONTMATTER NOTES — flat format, same as plan files. See
.claude/skills/plan-file-format.md.

  endpoint         the EP-### this contract belongs to
  method           GET | POST | PUT | PATCH | DELETE
  path             must match the route exactly — checked by contract_diff.py
  status_success   single success status code
  status_errors    every error status this endpoint returns
  permission       from the project's permission matrix
  tenant_scoped    true means a cross-tenant 404 test is MANDATORY
  idempotency_key  true on POST and non-idempotent PATCH where required
  pagination       none | cursor | offset
  errors           ERR-### codes referenced below
  requirements     REQ-### this endpoint satisfies

contract_diff.py compares the frontmatter against the live OpenAPI output.
The tables below are verified by the contract tests, not by the diff.
-->
