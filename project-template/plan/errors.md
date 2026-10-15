# Error Code Registry

Every error defined once. **No raw error strings anywhere in the codebase.**

---

## Rules

- **Derived during planning**, not invented during the build. Global codes at
  `/ingest-requirements`, story codes at `/plan-story`
- **Append-mostly.** Deprecate, never reuse — clients may be matching on codes
- **Technical codes are specific** — one per distinct failure you would want to
  find in logs
- **User codes are coarse** — if two failures lead to the same user action, they
  share a user code
- **Secrets and internals never appear** in user messages
- Every entry links to the `REQ-###` or `US-###` it came from

---

## Entry format

```
### ERR-001
**Status:** active | deprecated → ERR-###
**Technical:** DOMAIN_SUBJECT_CONDITION
**User code:** <client-facing code>
**HTTP:** <status>
**Category:** validation | authz | not-found | conflict | external | internal
**Source:** REQ-### | US-###

**User message:** <safe to display, no internals>
**Developer message:** <detail — logged, never returned outside debug>
```

---

## Envelope

All errors return one envelope: **user code**, **user message**, **correlation
ID**, plus field-level details for validation failures.

The technical code and developer message go to logs keyed by the same
correlation ID. A user quotes an ID from their screen; you find the exact
failure.

---

## Status mapping

| Category | Status |
|---|---|
| validation | 400 — business validation (Pydantic produces 422) |
| authz | 401 unauthenticated · 403 permitted-role failure |
| not-found | 404 — **including cross-tenant and soft-deleted** |
| conflict | 409 — state conflicts, duplicates, idempotency mismatch |
| external | 502 / 503 — adapter failures |
| internal | 500 — never leaks detail |

---

## Global — auth

*Derived at `/ingest-requirements`.*

*None yet.*

---

## Global — tenancy

*Cross-tenant access returns 404, never 403 — a 403 confirms the record exists.*

*None yet.*

---

## Global — validation

*None yet.*

---

## Global — pagination

*Invalid cursor, cursor from a different sort order, cursor past the end,
invalid sort field, page size above maximum.*

*None yet.*

---

## Global — idempotency

*Same key with a different request fingerprint.*

*None yet.*

---

## Domain

*Story-specific codes, grouped by domain. Derived at `/plan-story` — every
business rule that can be violated gets one.*

*None yet.*

---

## Deprecated

*Kept with a pointer to the replacement. Never deleted, never reused.*

*None yet.*
