# Skill: dal-conventions

**Tier:** invariant (tenant filter, soft-delete filter, tenant source) ·
default (pagination, async style)
**Read when:** writing or reviewing anything in `app/dal/`.

**References**
- Reads: `.claude/docs/design-spec.md` §5.3, §6, §8 ·
  `conventions.override.md` → section `dal-conventions`
- Related: `.claude/skills/layered-architecture.md`,
  `.claude/skills/service-conventions.md`,
  `.claude/skills/alembic-migrations.md`
- Called by: `.claude/commands/build-endpoint.md`
- Enforced by: `.claude/scripts/dal_guard.py` (hook `on_dal_edit`)

---

## The two mandatory filters *(invariant)*

Every query against a tenant-scoped table filters on **tenant**.
Every query against a soft-deleted table filters out **deleted** rows.

These are the same class of bug: forget either once and data crosses a boundary
or resurrects. They are not conditional on the caller, the role, or the use
case.

**Where tenant comes from:** the validated token context, passed down from the
router as a value. **Never** from the request body, a query parameter, a header,
or anything else a client controls. A client that can send it can change it.

`dal_guard.py` flags any query on a scoped table without both filters, and any
route reading tenant from user input.

### Deliberate exceptions

A query that genuinely must cross tenants (platform-admin reporting) is written
in a clearly named function marked as cross-tenant, and the reason is recorded
in `plan/decisions.md`. It is never the default shape of a function that also
serves tenant callers.

---

## What a DAL function does

**Does:** build and execute a query, apply the mandatory filters, apply
pagination, return models or row results.

**Does not:** decide whether something is allowed, raise business errors,
commit, call another DAL function to orchestrate a workflow, contain `if`
statements about business rules.

A DAL function that decides *whether* has taken a service's job.

### Session handling

The session is **passed in**. The DAL never creates one and never commits.
Transaction scope belongs to the caller — see `service-conventions`.

---

## Cursor pagination *(default)*

**Cursor is opaque and signed.** It encodes the sort field value plus a
tiebreaker, normally the ID. Signing prevents a client editing a cursor into
another tenant's range.

**Ordering must be on an immutable column.** Ordering by something that can
change — status, updated timestamp, a computed score — silently skips or
duplicates rows between pages.

**Shape:** the caller supplies a cursor and a limit; the DAL returns the page
plus the next cursor, or no cursor when the page is the last.

**Enforce a maximum limit.** An unbounded limit is a denial-of-service vector
and a memory problem.

**Required behaviours:**
- Invalid or unparseable cursor → error, never silently treated as page one
- Cursor issued under a different sort order → error
- Cursor past the end → empty page, no cursor
- Page size at the maximum → works; above the maximum → rejected or clamped
  (decide per project and record it)

Offset/limit is an override, not a default. If chosen, record the reason —
`docs/decisions.md` TD-015 explains what it costs.

---

## Soft delete

Deleted rows are excluded by default in every read path.

**Per-project decisions**, recorded in the project config:
- Does a soft-deleted record return 404 or 410?
- Is a unique value re-usable after deletion? If yes, the unique constraint
  must be a partial index that ignores deleted rows — a plain unique constraint
  will block re-registration forever.

**A hard-delete path**, if one exists at all, is a separate explicitly named
function, never a flag on the normal delete.

**Restore**, if supported, is a separate function and must re-check uniqueness —
the value may have been taken while the row was deleted.

---

## Async rules *(default: async)*

**Await the whole chain.** A missing `await` returns a coroutine object that
fails somewhere far away and confusingly.

**Never block the event loop.** A blocking call inside an async function
freezes *every* concurrent request, not just that one. This includes:
synchronous third-party SDKs, `requests`, file I/O, heavy CPU work, and any
library that does network calls without async support.

Anything blocking is pushed to a thread explicitly. `dal_guard.py` flags
suspected blocking calls inside async functions.

**Alembic runs sync.** Two engine configurations is expected and correct — not
a problem to solve.

---

## Query construction

- **Select explicit columns or the model** — never a bare select-all that pulls
  columns the caller does not need.
- **No N+1.** When a caller will need related rows, load them in the same query
  rather than in a loop. A DAL function called inside a loop by a service is a
  signal that the wrong function exists.
- **Bulk operations** take the filters as arguments; they still apply tenant and
  soft-delete filters.
- **Counts** are separate functions. Do not fetch a page to count it.
- **Existence checks** use an exists-style query, not a full fetch.

---

## Naming

Functions are named for what they fetch or change, with the tenant scoping
implied rather than spelled out — scoping is universal, so naming it adds noise.

Use a consistent verb set across the project: get (one, by identity), list
(many, paginated), create, update, soft_delete, restore, exists, count.

Cross-tenant functions break this pattern deliberately and are named so they
cannot be called by accident.

---

## Common violations

| Symptom | Fix |
|---|---|
| Tenant passed from the request body | Take it from token context in the router |
| Filter applied in the service instead of the DAL | Move it to the DAL — this is the invariant |
| `session.commit()` in a DAL function | Remove; the caller owns the transaction |
| Business rule inside a query builder | Move to the service |
| Pagination ordered by `updated_at` | Order by an immutable column |
| Unbounded limit | Enforce a maximum |
| DAL function called in a loop | Write a function that fetches the set |
| Soft-delete filter missing on a join | Apply it to every scoped table in the query, including joined ones |

---

## Overrides

Check `conventions.override.md` → section `dal-conventions` before applying
pagination style or async choice.

The two mandatory filters and the tenant source are **invariant** — no override
exists.
