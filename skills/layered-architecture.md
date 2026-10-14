# Skill: layered-architecture

**Tier:** invariant (the layering) · default (build order, sub-folder organisation)
**Read when:** building any endpoint, deciding where a piece of logic belongs,
or reviewing whether something is in the right layer.

**References**
- Reads: `.claude/docs/design-spec.md` §5, `conventions.override.md`
  → section `layered-architecture`
- Related skills: `.claude/skills/dal-conventions.md`,
  `.claude/skills/service-conventions.md`,
  `.claude/skills/router-conventions.md`,
  `.claude/skills/contract-authoring.md`
- Called by: `.claude/commands/build-endpoint.md`
- Checked by: `.claude/scripts/dal_guard.py`

---

## The layers

| Layer | Path | Owns |
|---|---|---|
| API | `app/api/` | Routing, dependency wiring, status codes |
| Schemas | `app/schemas/` | Pydantic request/response models |
| Services | `app/services/` | **All business logic** |
| DAL | `app/dal/` | Queries only |
| Models | `app/models/` | SQLAlchemy models |

Supporting, not layers: `app/auth/`, `app/errors/`, `app/adapters/`,
`app/utils/`, `app/settings.py`.

---

## What belongs where

### `app/api/` — routers

**Does:** declare the route, bind the permission, wire dependencies, pass
validated schema objects to a service, map the service result to a response
model and status code.

**Does not:** contain conditionals about business rules, query the database,
construct errors by hand, know about SQLAlchemy at all.

A router that is more than a handful of lines is usually holding logic that
belongs in a service.

### `app/schemas/` — Pydantic models

Request and response models. Written **at contract approval**, before any build
step, because they *are* the contract made executable.

Validation here is structural and field-level: types, ranges, lengths, formats,
enum membership. Rules that require looking at other records or current state
are business rules and belong in the service.

Separate models for request and response. Never return a model that would
expose internal columns.

### `app/services/` — business logic *(invariant)*

**Does:** enforce business rules, orchestrate multiple DAL calls, raise registry
errors, own the transaction boundary for a multi-step operation, call adapters.

**Does not:** build SQL, read request objects directly from FastAPI, know about
HTTP status codes, create or commit its own session.

A service receives an **injected session** and plain values or schema objects.
It returns domain results, not HTTP responses.

Rare exceptions where logic lives elsewhere must be recorded in
`plan/decisions.md`.

### `app/dal/` — data access

**Does:** build and execute queries. Nothing else.

**Always:** filters on tenant for tenant-scoped tables, filters soft-deleted
rows, applies cursor pagination per `dal-conventions`.

**Never:** business conditionals, raising business errors, committing.

Returns models or row results. A DAL function that decides *whether* something
is allowed has taken a service's job.

### `app/models/` — SQLAlchemy models

Table definitions and relationships. The base model carries `id`, `tenant_id`
where applicable, timestamps, and the soft-delete flag.

No query logic, no business methods.

---

## Dependency direction

Dependencies point **downward only**:

`api` → `schemas` → `services` → `dal` → `models`

- A service never imports from `api`
- A DAL function never imports a service
- A model never imports anything above it
- `errors/` and `settings.py` may be imported from anywhere
- `adapters/` is called from services only

An import that goes upward is a layering violation, not a shortcut.

---

## Build order per endpoint *(default)*

1. **Schemas** — already written at contract approval
2. **Model** — plus a migration if the schema changed
3. **DAL** — with tenant and soft-delete filters
4. **Service** — business logic, registry errors
5. **Router** — thin, permission-bound

Each step runs its tests before the next begins. Halt on failure per
`.claude/skills/testing-strategy.md`.

**Why bottom-up:** every layer is written against something real, so mocks are
needed only at the service-test boundary. Top-down means writing mocks that get
thrown away. Full reasoning: `docs/decisions.md` TD-002.

The contract still drives everything — it is approved before any of this starts,
and the tests exist before the build begins.

---

## Sub-folder organisation *(choice)*

Within each layer, group by **feature** or by **resource** — decided per project
during `/ingest-requirements` and recorded in the project config.

Whichever is chosen, it is applied consistently across all layers. A resource
that has a folder in `services/` has one in `dal/` with the same name.

Do not mix the two styles in one project.

---

## Where an endpoint's artifacts land

| Artifact | Location |
|---|---|
| Contract | `contracts/<api-path>/<method>.md` |
| Endpoint plan file | `plan/endpoints/EP-###.md` |
| Request/response models | `app/schemas/<group>/` |
| Model | `app/models/<group>.py` |
| Migration | `alembic/versions/` |
| DAL functions | `app/dal/<group>.py` |
| Service functions | `app/services/<group>.py` |
| Router | `app/api/<group>.py` |
| Error codes | `plan/errors.md` + `app/errors/` |
| Tests | `tests/` mirroring the layer structure |

---

## Common violations

| Symptom | Where it belongs |
|---|---|
| `if` on a business rule inside a router | service |
| Router importing a DAL function | service |
| DAL function raising a business error | service raises; DAL returns nothing or a row |
| Service calling `session.commit()` | caller owns the transaction (see `service-conventions`) |
| Service reading `Request` or `Depends` | router extracts, service receives values |
| Tenant filter applied in the service instead of the DAL | DAL — this is the invariant |
| Pydantic model doing a database lookup to validate | service |

---

## Overrides

Check `conventions.override.md` → section `layered-architecture` before applying
the build order or folder organisation.

The layering itself and the confinement of business logic to services are
**invariant** and cannot be overridden.
