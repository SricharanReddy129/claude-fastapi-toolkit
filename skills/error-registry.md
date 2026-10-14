# Skill: error-registry

**Tier:** invariant (no raw strings, no reuse, envelope) · default (shape,
derivation points)
**Read when:** raising any error, adding an error code, or designing a contract's
failure cases.

**References**
- Reads: `.claude/docs/design-spec.md` §9 ·
  `conventions.override.md` → section `error-registry`
- Related: `.claude/skills/service-conventions.md`,
  `.claude/skills/contract-authoring.md`,
  `.claude/skills/edge-case-checklist.md`
- Writes: `plan/errors.md`
- Called by: `.claude/commands/ingest-requirements.md`,
  `.claude/commands/plan-story.md`,
  `.claude/commands/add-error-code.md`

---

## One registry, every error defined once

Each entry carries:

| Field | Purpose |
|---|---|
| **ID** | `ERR-###`, permanent |
| **Technical code** | Stable, specific, for logs — e.g. `INV_STATE_INVALID_TRANSITION` |
| **User code** | Sent over the wire. **Coarser on purpose** — several technical codes may map to one |
| **HTTP status** | |
| **User message** | Safe to display. No internals, written for a human |
| **Developer message** | Detail. Logged, never returned outside debug |
| **Category** | validation · authz · not-found · conflict · external · internal |

The two-code split exists so you can distinguish failures precisely in logs
without leaking internal structure to clients.

---

## The envelope *(default)*

One envelope for all errors — not FastAPI's bare `detail`.

Carries: **user code**, **user message**, **correlation ID**, and field-level
details for validation failures.

The technical code and developer message go to logs keyed by the **same
correlation ID**. A user quotes an ID from their screen and you find the exact
failure.

Global exception handlers translate registry errors into this envelope. Routers
never build it.

---

## Invariants

**No raw error strings anywhere.** Every raise references a registry entry. No
ad-hoc messages, no `HTTPException` in services, no inline strings "just for
now". Flagged by `security-reviewer`.

**Codes are append-mostly.** Deprecate, never reuse — clients may be matching on
them. A deprecated code stays in the registry marked deprecated, with a pointer
to its replacement.

**Secrets never appear** in messages, developer messages, or logged detail.

---

## Codes are derived during planning, not invented during the build

| When | What is derived |
|---|---|
| `/ingest-requirements` | **Global** codes — auth failures, tenancy violations, validation, pagination, idempotency conflicts |
| `/plan-story` | **Story-specific** codes from that story's business rules — every rule that can be violated becomes a code, proposed alongside the contract |

Codes therefore exist **before** the code that raises them.

`/add-error-code` exists for genuine mid-build discovery, but it is the
exception. If the build needs a code that does not exist, that usually means a
business rule was missed during planning — worth noting, not just patching.

---

## Granularity

**Technical codes: specific.** One per distinct failure you would want to find
in logs. Each illegal state transition is its own code, not a shared
"invalid transition".

**User codes: coarse.** Collapse where the distinction would leak internals or
would not change what the user does. A client cannot act differently on
"record locked by another process" versus "record locked by a scheduled job" —
both are "temporarily unavailable".

The rule: if two failures lead to the same user action, they share a user code.

---

## Status mapping

| Category | Typical status |
|---|---|
| validation | 400 — business validation; Pydantic produces 422 |
| authz | 401 unauthenticated · 403 authenticated but not permitted |
| not-found | 404 — **including cross-tenant and soft-deleted** |
| conflict | 409 — state conflicts, duplicates, idempotency mismatch |
| external | 502 or 503 — adapter failures |
| internal | 500 — never leaks detail |

---

## Naming

Technical codes: `<DOMAIN>_<SUBJECT>_<CONDITION>`, uppercase with underscores.
The domain prefix makes log filtering by area trivial.

User codes are shorter and client-facing. They are part of your API surface —
treat them with the same stability commitment as a field name.

---

## Writing user messages

- States what happened and, where possible, what to do
- Never names a table, column, internal ID, service, or vendor
- Never includes a stack trace or exception text
- Avoids blame
- Is written once, in the registry — not reworded at each raise site

---

## Validation error details

Validation failures carry field-level details so a frontend can mark the right
input. Field paths match the request schema exactly.

This is the one place where per-raise variable content is expected — but the
code and the message template still come from the registry.

---

## Internal errors

Never leak detail. The user gets a generic message and the correlation ID.
Everything else goes to logs.

An unhandled exception reaching the client as a stack trace is a defect, not a
debugging convenience.

---

## Registry file

Lives at `plan/errors.md`. Each entry carries its ID, both codes, status,
category, both messages, status (active or deprecated), and the requirement or
story IDs it came from.

Grouped by domain. Links back to requirements make it traceable like everything
else in `plan/`.

---

## Common violations

| Symptom | Fix |
|---|---|
| Raw string in a raise | Add or use a registry entry |
| `HTTPException` in a service | Raise a registry error; handler maps it |
| Same code reused for two different failures | Split them |
| Technical detail in a user message | Move it to the developer message |
| Code invented during the build | Check the registry; if genuinely new, note the planning gap |
| Deleted code | Deprecate instead |
| Error envelope built in a router | Global handler does it |
| Missing correlation ID | Add — it is what makes logs usable |

---

## Overrides

Check `conventions.override.md` → section `error-registry` for envelope shape
and derivation points.

No raw strings, no code reuse, and no secrets in messages are **invariant**.
