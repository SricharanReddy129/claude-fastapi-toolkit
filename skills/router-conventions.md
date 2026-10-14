# Skill: router-conventions

**Tier:** invariant (thinness, tenant source, permission binding) ·
default (naming, status codes)
**Read when:** writing or reviewing anything in `app/api/`.

**References**
- Reads: `.claude/docs/design-spec.md` §5, §6.2, §7, §9.2 ·
  `conventions.override.md` → section `router-conventions`
- Related: `.claude/skills/layered-architecture.md`,
  `.claude/skills/service-conventions.md`,
  `.claude/skills/contract-authoring.md`,
  `.claude/skills/error-registry.md`
- Called by: `.claude/commands/build-endpoint.md`

---

## Routers are thin *(invariant)*

A route declares itself, wires dependencies, calls one service function, and
maps the result to a response model and status code.

**No business conditionals. No database access. No error construction.**

If a route has branching logic about what the business should do, that logic
belongs in a service.

---

## The five things a route does

1. **Declare** method, path, response model, status code, and permission
2. **Receive** the validated request schema as a parameter
3. **Extract** caller context — tenant, user, roles — from the validated token
   context, and the session from the session dependency
4. **Call** one service function with plain values
5. **Return** the result, serialised by the response model

Anything beyond these five is misplaced.

---

## Caller context *(invariant)*

Tenant, user, and roles come from the **validated token context** established by
middleware. The router passes them explicitly to the service.

**Never** read tenant from a path parameter, query string, body field, or
custom header. A client that can send it can change it. Flagged by
`dal_guard.py`.

The one legitimate tenant-shaped path parameter is on platform-admin routes that
are explicitly cross-tenant — and those carry their own permission and are
recorded in `plan/decisions.md`.

---

## Permissions

Every route declares the permission it requires. Middleware enforces it; the
router only names it.

**The realistic bug is a route bound to the wrong permission**, which is why
every endpoint carries a role-binding test — one allowed role passes, one
disallowed role gets 403. See `testing-strategy`.

Permission names come from the project's permission matrix, derived from the
requirements document. A route must never invent one.

---

## Paths and naming *(default)*

- Versioned prefix, resource-oriented, plural nouns
- Nesting only where the child genuinely cannot exist without the parent
- No verbs in paths for CRUD; a named action on a resource is acceptable as a
  sub-path when it is a real state transition rather than an update
- Path parameters are identifiers only, never filters

The contract is authoritative for the exact path. If the contract and the route
disagree, that is a stop condition — see `contract-authoring`.

---

## Status codes *(default)*

| Situation | Code |
|---|---|
| Read success | 200 |
| Create success | 201 |
| Update success | 200 |
| Accepted for async processing | 202 |
| Delete success, nothing returned | 204 |
| Validation failure | 422 (Pydantic) or 400 (business validation) |
| Unauthenticated | 401 |
| Authenticated, role not permitted | 403 |
| Not found, or belongs to another tenant | **404** |
| State conflict, duplicate, idempotency mismatch | 409 |

**Cross-tenant is 404, never 403** — a 403 confirms the record exists.

The status code is declared on the route and asserted in the contract test.

---

## Responses

- Every route declares a response model. Never return a bare model that may
  expose internal columns
- List routes return the paginated envelope with the page and the next cursor
- Errors are never constructed in the router — registry errors raised by
  services are translated by the global exception handlers into the standard
  envelope

---

## Dependencies

Routes compose dependencies rather than doing work inline: the session,
the validated token context, pagination parameters, the idempotency key where
required.

A dependency that performs business validation is misplaced — it belongs in the
service. Dependencies exist to supply things, not to decide things.

---

## Router registration

One router module per resource or feature group, matching the service and DAL
grouping chosen for the project. Routers are assembled centrally with their
prefixes and tags; a router module does not register itself.

---

## Common violations

| Symptom | Fix |
|---|---|
| `if` on a business rule in a route | Move to the service |
| Route imports a DAL function | Call a service |
| Tenant read from path or body | Take it from token context |
| `HTTPException` raised in a route | Service raises a registry error |
| Route returns a model directly | Declare a response model |
| Route commits the session | Caller/dependency owns the transaction |
| Permission invented rather than taken from the matrix | Use the matrix name |
| Path disagrees with the contract | **Stop** — contract mismatch |
| Try/except around a service call to map a status | Let the global handler do it |

---

## Overrides

Check `conventions.override.md` → section `router-conventions` before applying
path naming or status code conventions.

Thinness, tenant source, and permission binding are **invariant**.
