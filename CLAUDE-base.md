# Toolkit Base Conventions

Loaded every session. Kept short on purpose.
Full reasoning lives in `.claude/docs/design-spec.md` — read the section you
need, never the whole file.

---

## Resolution order

1. **Invariants** below — cannot be overridden
2. **`conventions.override.md`** (project root) — supersedes defaults, sectioned
   by skill name; read only the relevant section
3. **`.claude/skills/*.md`** — defaults

Before applying any default, check the override file's section for the skill
you are working under.

---

## Invariants

Never overridden. No flag exists. Violating one is a bug, not a style choice.

**Tenancy**
- Every query on a tenant-scoped table filters on tenant
- Every query on a soft-deleted table filters deleted rows
- `tenant_id` comes from the validated token context only — never from body,
  query string, or header
- Cross-tenant access returns 404, not 403

**Auth**
- `algorithms`, `aud`, `iss` passed explicitly on every token decode
- `typ` claim validated — identity tokens rejected on business routes
- Every claim read from the verified payload, never the unverified header

**Code**
- Business logic lives in `app/services/` — not routers, not DAL
- Services accept an injected session; they never create or commit one
- No raw error strings — every raise references the error registry
- No `os.getenv` outside `app/settings.py`
- No blocking call inside an async function without explicit thread offload

**Tooling**
- Dependencies only via `poetry add`; everything runs via `poetry run`
- Never read `.env` or `.env.*`. `.env.example` is the committed contract
- A new dependency is announced, never added silently

**Tests**
- No test commits, truncates, or drops. Isolation is transaction rollback
- Tests mint real tokens via the factory — never an auth-bypass flag
- **Fix code, never tests, without asking**

**Plan files**
- Links point upward only. Downward indexes are generated, never hand-edited
- IDs are permanent and never reused
- Every cross-reference is a repo-relative path, never a bare name

---

## Stop and ask

Halt immediately, write the question to `plan/questions.md`, and report:

- Ambiguity not covered by contract or conventions **that changes behaviour**
- Anything contradicting the contract
- A logic-class test failure (code and test both plausible)
- A breaking contract change
- A new dependency
- Two failed fix attempts on the same failure
- Infrastructure failure (DB down, missing migration, bad env)

**Do not stop** for cosmetic gaps — follow conventions, note it, continue.

---

## Test failure handling

Classify before touching anything:

| Class | Action |
|---|---|
| Mechanical (import, typo, fixture name, missing await, signature) | Fix, note in summary |
| Logic (both readings plausible) | **Stop, show both, ask** |
| Contract mismatch | **Stop always** |
| Infrastructure | **Stop and report** |

Budget: **two** attempts, then stop with everything tried.

---

## State lives in files

Never only in conversation. Phases, stories, contracts, decisions, open
questions, endpoint status — all written to `plan/`.

Every command must be resumable by a session that did not run the previous one.

---

## Progress output

One line per event, prefixed with the endpoint ID. Announce: current story and
endpoint, layer being written, migration generated, test file running,
pass/fail counts, moving to next endpoint.

No paragraphs between steps. Stops print what is needed, not buried in prose.

---

## Where things are

| Need | Path |
|---|---|
| Full reasoning | `.claude/docs/design-spec.md` |
| Why a default is the default | `.claude/docs/decisions.md` |
| What is overridable | `.claude/docs/conventions-index.md` |
| Conventions and procedures | `.claude/skills/` |
| Stage entry points | `.claude/commands/` |
| Deterministic checks | `.claude/scripts/` |
| Project state | `plan/index.md` |
| Contracts | `contracts/` |
| Project overrides | `conventions.override.md` |

---

## Stack

Python · FastAPI · Poetry · Pydantic · SQLAlchemy (async app, sync Alembic) ·
Alembic · pytest · PyJWT · PostgreSQL or MySQL

Multi-tenant. First-party self-issued auth, two token types. Cursor pagination.
Soft delete. Idempotency keys. Central error registry.
