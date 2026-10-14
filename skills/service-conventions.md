# Skill: service-conventions

**Tier:** invariant (logic location, injected session, registry errors) ·
default (structure, naming)
**Read when:** writing or reviewing anything in `app/services/`.

**References**
- Reads: `.claude/docs/design-spec.md` §5, §8.3, §8.5, §9 ·
  `conventions.override.md` → section `service-conventions`
- Related: `.claude/skills/layered-architecture.md`,
  `.claude/skills/dal-conventions.md`,
  `.claude/skills/error-registry.md`,
  `.claude/skills/testing-strategy.md`
- Called by: `.claude/commands/build-endpoint.md`
- Enforced by: `.claude/scripts/dal_guard.py`, `security-reviewer`

---

## The service layer owns the business *(invariant)*

All business logic lives here. Not in routers, not in the DAL, not in Pydantic
validators.

If a rule requires looking at current state, another record, or the caller's
role beyond route-level permission, it is a business rule and it belongs here.

Rare exceptions must be recorded in `plan/decisions.md` with a reason.

---

## Sessions and transactions *(invariant)*

**A service accepts an injected session. It never creates one and never
commits.**

Two independent reasons:

1. **Atomicity.** A multi-step operation that commits midway leaves the system
   in a half-applied state when a later step fails.
2. **Testability.** The test fixture owns a transaction it rolls back. A
   service that commits internally escapes that rollback and writes to real
   data — see `testing-strategy`.

The transaction boundary is owned by whatever wires the request: the session
dependency opens it, the request either succeeds and it commits, or raises and
it rolls back. A service signals failure by raising, never by committing a
partial result.

**Nested calls:** a service calling another service passes the same session.
Never open a second one.

---

## What a service does

**Does:** validate business rules · orchestrate multiple DAL calls · enforce
state transitions · raise registry errors · call adapters · compute derived
values · handle idempotency.

**Does not:** build queries · know HTTP status codes · read FastAPI request
objects · construct response envelopes · catch its own errors to return a
status.

### Inputs and outputs

A service receives plain values or schema objects plus the session and the
caller context (tenant, user, roles). It returns domain results — a model, a
list, a value, or nothing.

It never returns an HTTP response, a status code, or a serialised envelope.
Mapping to HTTP is the router's job.

---

## Caller context

The router extracts tenant, user, and roles from the validated token context
and passes them as explicit arguments. A service never reaches for request
state and never trusts a tenant value that came from the request body.

Route-level permission is already enforced by middleware. A service re-checks
only rules middleware cannot know — for example, whether this particular record
is in a state this role may act on.

---

## Errors *(invariant)*

Every failure raises an error that references an entry in the error registry.
No raw strings, no ad-hoc exception messages, no `HTTPException` in a service.

See `.claude/skills/error-registry.md`. If the rule being enforced has no code
yet, that is a planning gap — stop and ask rather than inventing one inline.

---

## State transitions

When a record has a lifecycle, the allowed transitions are declared explicitly
in one place, not scattered as conditionals across functions.

Every transition attempt validates against that declaration and raises a
registry error on an illegal move. Each illegal transition is a named error
code, not a generic conflict.

Acting on an already-processed record is an illegal transition, not a
no-op — unless idempotency explicitly applies.

---

## Idempotency

For operations marked as requiring a key (project choice):

1. The key is captured **before** processing, so two concurrent duplicates do
   not both execute
2. Same key + same request fingerprint → return the stored response
3. Same key + different fingerprint → conflict error

The stored record carries key, tenant, endpoint, request fingerprint, response,
and status. Idempotency is per tenant — a key from one tenant never matches
another's.

---

## Adapters

Third-party calls go through `app/adapters/`, never directly from a service.

Rules:
- The adapter owns retries, timeouts, and translating vendor errors into
  registry errors
- A service never sees a vendor-specific exception type
- Any synchronous vendor SDK is wrapped to run off the event loop
- Adapter failure is a registry error in the `external` category, never an
  unhandled exception

---

## Settings *(invariant)*

Configuration is read from the single typed settings object. **No `os.getenv`
outside `app/settings.py`** — scattered environment reads are what make a
project impossible to configure for a new environment.

Flagged by `dal_guard.py`.

---

## Structure and naming

One module per resource or feature, matching the DAL and router grouping chosen
for the project.

Functions are named for the business operation, not the data operation —
`approve_invoice`, not `update_invoice_status`. If the name is a CRUD verb, the
service may be a pass-through that should not exist.

**Pass-throughs are a smell but not forbidden.** A service that only forwards to
the DAL is fine when the operation genuinely has no rules yet; it gives rules a
place to land later. Just do not invent ceremony around it.

---

## Common violations

| Symptom | Fix |
|---|---|
| `session.commit()` in a service | Remove — caller owns the transaction |
| Service opens its own session | Accept it as an argument |
| `HTTPException` raised in a service | Raise a registry error; the router maps it |
| Raw string error message | Add or use a registry code |
| `os.getenv` in a service | Read from the settings object |
| Service reads `Request` or uses `Depends` | Router extracts, service receives values |
| Query built in a service | Move to the DAL |
| Status transition checked ad hoc in two places | Declare transitions once |
| Vendor exception escaping a service | Adapter translates it |

---

## Overrides

Check `conventions.override.md` → section `service-conventions` before applying
structure or naming conventions.

Logic location, injected sessions, and registry errors are **invariant**.
