# Claude FastAPI Toolkit — Design Specification

**Status:** v1 design, settled
**Owner:** Sri Charan
**Purpose:** Single source of truth for every architectural and process decision
behind this toolkit. If any other file in this repo contradicts this document,
this document wins until it is explicitly amended.
claude-fastapi-toolkit
---

## 0. How to use this document

Read the section you need, not the whole file.

| You are doing this | Read |
|---|---|
| Building an endpoint | §5, §6, §8, §9, §10 |
| Building auth | §7, §6 |
| Writing or changing a migration | §11 |
| Planning requirements / stories | §12, §13 |
| Handling a requirement change | §14 |
| Changing the toolkit itself | §2, §3, §16 |

Every decision below carries its rationale. Do not reverse a decision without
recording the reversal in `docs/decisions.md`.

---

## 1. What this toolkit is

A per-project Claude Code configuration for building multi-tenant FastAPI
applications in a layered architecture, with a traceable requirement → story →
endpoint → contract → test pipeline.

**Stack (fixed across projects):**

- Python, FastAPI
- Poetry (dependency management)
- Pydantic (validation / schemas)
- SQLAlchemy — **async** for the application, **sync** for Alembic
- Alembic (migrations)
- pytest
- PyJWT — first-party auth, self-issued tokens
- PostgreSQL or MySQL (per project)

**Non-goals for v1:** deployment/infra, Docker, SSO federation, OpenID Provider
conformance, MCP servers.

---

## 2. Distribution and update model

### 2.1 Layout

The toolkit is a standalone git repo. Its contents sit at the repo root — there
is no wrapper folder. A project consumes it by cloning it into `.claude/`:

```
cd my-project
git clone <toolkit-url> .claude
```

The project's `.gitignore` excludes `.claude/.git` so the two repos do not
interfere.

**There is no permanent machine-level clone.** The toolkit is per project, not
per device. You edit the toolkit from inside whichever project you are working
in.

### 2.2 The three change cases

**Case 1 — project-specific change.**
Goes in `conventions.override.md` at the project root. Committed to the
*project* repo. Never travels to the toolkit.

**Case 2 — universal change.**
Edit the file inside `project/.claude/` directly. Run `/promote-to-toolkit`,
which commits and pushes to the toolkit repo's `main` branch from inside
`.claude/`. The project is immediately on that commit, because it *is* that
commit. No copy-down step, no drift window.

**Case 3 — pulling improvements made elsewhere.**
`/update-toolkit` runs `git pull` inside `.claude/`. If uncommitted local
changes exist there, it stops and asks whether to promote them first.

### 2.3 The failure mode this prevents

An edit inside `.claude/` that is neither pushed to the toolkit nor moved to the
override file is an undecided state — this project silently has a private
version of a skill. `/toolkit-status` surfaces uncommitted changes in `.claude/`
for exactly this reason.

### 2.4 Mid-project updates

Allowed, but **only between stories, never mid-story**. A convention changing
under a half-built story produces inconsistency between endpoints.

---

## 3. Convention tiers

Every rule in this toolkit carries one of three tiers, stated next to the rule.

**Invariant — never overridable.**
Overriding one is a bug, not a preference. No config switch exists, because a
switch that exists will eventually be flipped at 11pm. Enforced by hooks and
scripts where mechanically possible.

Current invariants:
- Tenant filter on every query against a tenant-scoped table
- Soft-delete filter on every query against a soft-deleted table
- `algorithms`, `aud`, `iss` passed explicitly on every token decode
- Tenant identity never read from user input
- No raw error strings — every error references the registry
- No secrets in committed files
- Services accept an injected session; they never create or commit one
- Dependencies enter only via `poetry add`

**Default — overridable with a logged reason.**
Ships with a value and a rationale. A project may override in
`conventions.override.md` with a reason and a date.

Examples: cursor pagination, 15-minute access token lifetime, argon2,
error envelope shape, layer build order.

**Choice — decided per project, no default.**
Expected to differ every time. Derived from the requirements document and
confirmed by the user during `/ingest-requirements`.

Examples: database engine, role names and permission matrix, which entities are
tenant-scoped, which operations require idempotency, soft-delete scope.

### 3.1 Override resolution

`CLAUDE.md` (project root) declares the resolution order:

1. Invariants from `.claude/` — cannot be overridden
2. `conventions.override.md` — supersedes defaults
3. `.claude/skills/*` — defaults

`conventions.override.md` is **sectioned by skill name**, so a skill reads only
its own section rather than the whole file.

### 3.2 Feedback loop

If the same override appears in three projects, it should stop being an override
and become either a new default or an explicit project choice. Review override
files periodically — this is the best signal for what the next toolkit version
should contain.

---

## 4. Project structure

```
project/
├── CLAUDE.md                   # thin; points at .claude/ and overrides
├── conventions.override.md     # project deltas, sectioned by skill
├── pyproject.toml
├── .env.example                # committed; the config contract
├── .claude/                    # the toolkit clone
├── plan/                       # see §12
├── contracts/                  # mirrors API path structure
├── alembic/
├── app/
│   ├── main.py
│   ├── settings.py             # the ONLY place env is read
│   ├── api/                    # routers — thin
│   ├── schemas/                # Pydantic request/response models
│   ├── services/               # business logic
│   ├── dal/                    # data access
│   ├── models/                 # SQLAlchemy models
│   ├── auth/                   # token issuance, validation, RBAC, keys
│   ├── errors/                 # registry, envelope, handlers
│   ├── adapters/               # third-party integrations
│   └── utils/
└── tests/
```

**`infra/` is deliberately absent from v1.** Scaffolding a folder with no
conventions behind it invites invented structure that cannot be evaluated.

**Sub-folder organisation within each layer is per project** — grouped by
feature or by resource, decided at `/ingest-requirements` time.

---

## 5. Architecture and layering

### 5.1 The layers

| Layer | Responsibility |
|---|---|
| `api/` | Routing, dependency wiring, status codes. Thin. No business logic. |
| `schemas/` | Pydantic validation. Request/response models passed as parameters. |
| `services/` | All business logic. Raises registry errors. Owns transaction scope. |
| `dal/` | Queries only. Tenant + soft-delete filtering. No business rules. |
| `models/` | SQLAlchemy models. |

Business logic lives in `services/` — not in routers, not in the DAL. Rare
exceptions must be logged as decisions.

### 5.2 Build order per endpoint

**Schemas (written at contract approval) → model → DAL → service → router.**

Rationale for bottom-up: every layer is written against something real, so
mocks are needed only at the service-test boundary. Top-down means writing
mocks that are thrown away as the real layers land.

The contract still drives everything — it is written and approved first. What
is *not* done is writing a failing API test first and building downward to
satisfy it; the contract plus upfront tests already serve that purpose.

### 5.3 Async rules

Async SQLAlchemy is the default. The reasons it is chosen are concurrency under
slow I/O (notably LLM adapters), not any notion that async is a free superset
of sync.

**Costs that must be actively managed:**
- Every DAL call must be awaited through the whole chain
- Any blocking call inside an async handler freezes the event loop for *all*
  concurrent requests — third-party sync SDKs, `requests`, heavy CPU work, file
  I/O must be pushed to a thread explicitly
- The driver must be async (asyncpg, or psycopg 3 in async mode)
- Alembic runs sync regardless — two engine configurations are expected and
  normal

`dal_guard` flags blocking calls inside async functions.

---

## 6. Multi-tenancy

### 6.1 The model

**Identity is global. Authorization is per membership.** Three tables, not two:

- `users` — no tenant column. Email globally unique. Credentials live here.
- `memberships` — user × tenant, carrying **the roles held in that tenant** and
  a status.
- everything else — tenant-scoped.

Roles live on the membership, never on the user. A user who is admin in tenant A
and viewer in tenant B is the normal case.

### 6.2 Where isolation is enforced

Middleware **can** decide: is the token valid, who is the caller, which tenant,
which roles, is this role permitted to call this route at all.

Middleware **cannot** decide whether a specific record belongs to the caller's
tenant — it has no idea what `invoice_id=4471` refers to.

**Therefore tenant isolation is a DAL concern, enforced structurally.**
Every query against a tenant-scoped table filters on tenant. `tenant_id` comes
from the validated token context and **never** from the request body, a query
parameter, or a header. If a client can send it, a client can change it.

### 6.3 Three enforcement points

1. No DAL method on a tenant-scoped table without a tenant filter (`dal_guard`)
2. No route reads tenant from user input (`dal_guard`)
3. No service method trusts a tenant value passed up from the API layer

### 6.4 Cross-tenant access returns 404

Not 403. A 403 confirms the record exists, which leaks information across
tenants.

---

## 7. Authentication — Phase 0

### 7.1 Scope

**First-party auth with OIDC-shaped tokens.** Not an OpenID Provider.

Out of scope entirely: client registration, consent screens, authorization code
flow, PKCE, discovery documents, third-party clients, SSO federation.

Each platform has its own issuer and its own keys; all tenants of that platform
share it. A token from one platform is structurally invalid against another.

Auth is **in-repo**, instantiated per project from this toolkit — not a shared
service.

### 7.2 Why auth is built before any business endpoint

Tenant ID and roles come from the token context, and every DAL query filters on
tenant. Stubbing that means rewriting every endpoint and every test when real
auth lands. It is the most expensive retrofit on the list.

### 7.3 The two-token model

**Identity token** — issued at login. Identifies the user. Carries **no tenant**.
Authorized to call exactly two things: list my tenants, and exchange for an
access token.

**Access token** — issued by exchange. Carries user + **one tenant** + the roles
held in that tenant. Required by every business endpoint.

A `typ` claim distinguishes them and **is validated**. Middleware rejects an
identity token on a business route and an access token on the exchange route.

**Rejected alternative:** one token listing all memberships, with an
active-tenant header. This fails because tenant would then arrive from user
input (§6.2). Putting tenant in the signed token means switching tenants
requires proving membership again.

### 7.4 Tier 1 — built in v1

- **Asymmetric keys with `kid` in the header.** Symmetric HS256 would work for a
  single service, but `kid` is what makes rotation possible later without
  changing the token format. Costs about an hour; skipping it is a migration.
- **Short access tokens (15 min) + refresh tokens.** This is what makes
  revocation mostly unnecessary — a removed user is locked out within 15 minutes
  automatically. Long-lived access tokens are what force complicated revocation
  machinery.
- **Refresh rotation with reuse detection.** Each refresh issues a new token and
  invalidates the old. An already-used token coming back means theft → the
  entire family is revoked. Retrofitting this breaks clients, so it is v1.
- **Refresh family revocation** — free once rotation exists. Gives
  logout-everywhere and admin-force-logout.
- **Membership re-checked at exchange.**
- **argon2** for password storage.
- **Test token factory** — built alongside issuance.

### 7.5 Tier 2 — seam designed, built later

JWKS endpoint (trivial once keys are stored properly; nothing needs it until a
second service validates tokens), key rotation tooling, MFA, password reset.

### 7.6 Transport — cross-origin

Frontend and API are **cross-origin**. Therefore:

- Refresh token in an **httpOnly cookie**, `Secure`, `SameSite=None`,
  `Path` scoped to the refresh/logout endpoints only, explicit `Max-Age`
- Because `SameSite=None` allows cross-site sending, **CSRF token validation on
  the refresh endpoint is mandatory and is part of Phase 0**, not deferred
- **CORS with an explicit origin allowlist.** Never `*` with credentials
- Access token stays in the **response body**, held in frontend memory, sent as
  a bearer header. Never a cookie — mixing both makes every endpoint
  CSRF-exposed

### 7.7 PyJWT — the four traps

PyJWT is deliberately unopinionated. These are invariants, checked by
`security-reviewer`:

1. **Pass `algorithms` explicitly on every decode.** Omitting it is how
   `alg: none` and HS/RS confusion attacks land. Single most important line in
   the auth code.
2. **`aud` and `iss` are not validated unless passed.** PyJWT validates expiry
   by default; it does not validate these.
3. **JWKS is not automatic** — key generation, storage, rotation and `kid`
   handling are your code.
4. **Every claim read from the verified payload** — never from the unverified
   header, never from a decode-without-verify call.

Use a maintained JWT library. Writing the protocol is defensible; writing the
crypto is not.

### 7.8 Phase 0 build order

1. Models + migration: users, memberships, refresh tokens, signing keys
2. Key generation and storage, `kid` support
3. Token issuance: identity token, then access token via tenant exchange
4. Validation middleware: signature → `algorithms` → `aud` → `iss` → `typ` →
   expiry → tenant and role context
5. RBAC matrix (from the requirements doc), enforced in middleware
6. Refresh rotation, reuse detection, grace window
7. Cookie + CSRF + CORS
8. Endpoints: login, logout, token exchange, list-my-tenants
9. Test token factory
10. Middleware test suite (deep — see §10.3)

### 7.9 Known operational wrinkles

**Concurrent refresh races.** Multiple tabs or a retrying mobile client can fire
two refreshes with the same token and trip reuse detection, logging the user out
for no reason. Mitigation: a short grace window where a just-rotated token is
still accepted; only genuine later reuse triggers revocation. Design it in.

**Expiry is constant.** 15-minute tokens mean expiry happens during normal use.
The client needs a clean refresh-on-401-then-retry path, and tests must cover
the expired-token path properly.

---

## 8. Data access conventions

### 8.1 Cursor pagination *(default)*

- Opaque cursor encoding the sort field plus a tiebreaker (usually the ID)
- **Cursor is signed**, so clients cannot forge one into another tenant's range
- **Ordering must be on an immutable column.** Ordering by a mutable column
  silently skips or duplicates rows
- Test categories: invalid cursor, cursor from a different sort order, cursor
  past the end

### 8.2 Soft delete

A second mandatory DAL filter alongside tenant scoping — same class of bug,
forget it once and deleted records reappear.

Per-project decisions:
- Does a soft-deleted record return 404 or 410?
- Can a unique value be re-used after deletion? (Usually requires a partial
  unique index.)

### 8.3 Idempotency

Required on POST and any non-idempotent PATCH. Stored key table: key, tenant,
endpoint, request fingerprint, response, status.

Three rules:
1. Same key + same request → return the stored response
2. Same key + **different** request → 409
3. The key is captured **before** processing, so concurrent duplicates do not
   both execute

Mandatory test category on those endpoints.

### 8.4 Audit

v1: **middleware-level, platform-admin purposes only.**

**Stated limitation:** middleware sees the request and the response, not the
before/after of a row. You get "admin X called PATCH /invoices/44 at 10:02 and
got 200", not "status went from draft to approved". Field-level history for
tenants is a DAL-level concern and a different mechanism, added as a feature if
required.

### 8.5 Sessions

Services accept an **injected** session and never create or commit one.
*(Invariant.)* This is what makes a multi-step operation atomic, and it is also
what keeps the test transaction in control (§10.5).

---

## 9. Error handling

### 9.1 Registry

One central registry. Every error defined once, carrying:

| Field | Purpose |
|---|---|
| Technical code | Stable, specific, for logs. e.g. `INV_STATE_INVALID_TRANSITION` |
| User code | Sent over the wire. Coarser on purpose — several technical codes may map to one |
| HTTP status | |
| User message | Safe to display, no internals |
| Developer message | Logged, never returned outside debug environments |
| Category | validation / authz / not-found / conflict / external / internal |

### 9.2 Envelope

One envelope for all errors — not FastAPI's bare `detail`. Carries the user
code, user message, and a **correlation ID**. The technical code and developer
message go to logs keyed by the same correlation ID, so a user can quote an ID
from a screen and the exact failure is findable.

### 9.3 Rules

- **No raw error strings anywhere.** Every raise references a registry entry.
  *(Invariant.)*
- The registry is **append-mostly**. Codes are deprecated, never reused —
  clients may match on them.

### 9.4 Codes are derived, not hand-added

- `/ingest-requirements` extracts **global** codes: auth failures, tenancy
  violations, validation, pagination, idempotency conflicts
- `/plan-story` extracts **story-specific** codes from that story's business
  rules — every rule that can be violated becomes a code, proposed alongside
  the contract

Codes therefore exist before the code that raises them. `/add-error-code`
remains available for genuine mid-build discovery, but it is the exception.

---

## 10. Testing strategy

### 10.1 What was deliberately rejected

"Unit tests at every layer + integration tests per layer + request tests per
endpoint" was rejected as unmaintainable and low-value. Two specific reasons:

- "Integration testing per layer" is not a coherent category — integration
  happens *between* layers. A service tested against a mocked DAL is still a
  unit test with a more elaborate mock.
- The API and DAL layers are mostly plumbing. Unit-testing a router in isolation
  asserts that a mock was called with arguments you chose. It passes forever and
  catches nothing.

### 10.2 What is tested, per endpoint

- **Service-layer unit tests** — one per meaningful branch (authz failure,
  validation rejection, state transition, edge case). This is where logic lives,
  so this is where mocks earn their keep.
- **Utils/validators** where real logic exists.
- **One integration test per endpoint** through the real stack — happy path plus
  the failures that matter. This catches wiring bugs, and wiring is where
  FastAPI projects break.
- **Contract assertions** — response shape matches the committed contract.
- **DAL** — tested per non-trivial query, not per endpoint.

### 10.3 Auth testing

Because auth and RBAC live in middleware, endpoints are free of that duty.

**Tested once, deeply — the middleware.** Missing token, malformed, expired,
wrong signature, wrong issuer, wrong audience, wrong algorithm, tampered
payload, valid-but-revoked, wrong `typ`, every role against every permission in
the matrix. One-time investment covering every endpoint forever.

**Tested per endpoint — exactly two things:**
1. **Role binding** — one allowed role passes, one disallowed role gets 403.
   Catches the realistic bug: a route annotated with the wrong permission.
2. **Cross-tenant returns 404** — valid token from tenant A requesting tenant
   B's record. **Mandatory on every endpoint touching tenant data, no
   exceptions.** This is the test that catches a missing DAL filter.

The permission matrix can generate the middleware's permission tests, so adding
a role automatically expands coverage.

### 10.4 Token factory, not a bypass flag

Tests mint tokens directly via a fixture that takes tenant and roles. Cross-
tenant tests become one-liners.

**Anti-pattern deliberately avoided:** a config flag that disables auth in test
mode. It makes tests easy and eventually ships to production. The token factory
gives the same convenience while exercising the real middleware on every
request — which is what you want, since that middleware is the only thing
standing between tenants.

### 10.5 Database isolation — single database

**One database for dev and test.** Isolation comes from transactions:

The session fixture opens a transaction, the test runs, the transaction is
**rolled back unconditionally**. Nothing is ever committed, so dev data is never
touched — tests cannot see it and cannot modify it.

Three rules make this hold:
1. **No test ever commits.** The fixture owns the transaction.
2. **No test truncates or drops.** Hook-blocked: `TRUNCATE`, `DROP`,
   `metadata.drop_all` in the test tree.
3. **Tests create their own data** inside the transaction and assume nothing
   pre-exists.

**Known limitation:** anything genuinely requiring a commit (real concurrency
behaviour) cannot be tested this way. Mitigated by §8.5 — services take an
injected session rather than committing internally.

A fixture assertion verifies the DB URL matches what the test config declares,
so a misconfigured run fails loudly.

### 10.6 Tests are written upfront, by a subagent

Tests are authored **from the contract, before implementation**, by the
`test-author` subagent.

Rationale: a test written after seeing the implementation tends to test what the
code does rather than what the contract promised. A separate context keeps
implementation details out of the tests.

`/build-endpoint` therefore runs against a suite that already exists and is red.
The build is done when it is green.

### 10.7 Edge-case checklist

Walked for every endpoint. The test file records which categories were
considered and which are N/A — so "did we cover enough" has an auditable answer.

- **Auth** — missing, expired, malformed, valid-but-wrong-role, valid-but-other-tenant
- **Resource** — not found, soft-deleted, belongs to another tenant
- **Validation** — missing required, wrong type, empty string vs null, oversized,
  out of range, invalid enum, unexpected extra fields, unicode/emoji,
  whitespace-only
- **Numeric/money** — zero, negative, precision and rounding, very large
- **Dates** — end before start, past/future constraints, timezone, naive vs aware
- **State** — illegal transitions, already-processed, idempotency on duplicate submit
- **Concurrency** — double submit, stale update
- **Collections** — empty, exactly one, max page size, page past the end,
  invalid sort field
- **Referential** — nonexistent FK, unique violation, delete with children
- **PATCH semantics** — field omitted vs explicitly null
- **Cursor** — invalid, wrong sort order, past the end

Most endpoints mark half of these N/A. The value is that the question was asked.

### 10.8 Test failure pipeline

**Claude may fix the code. Claude may never silently fix a test.** A test
encodes the approved contract; if a test is wrong, the contract was wrong, and
that is a conversation.

Failures are **classified before anything is touched**:

| Class | Action |
|---|---|
| **Mechanical** — import error, typo, wrong fixture, missing await, signature mismatch | Fix silently, note in summary |
| **Logic** — code does X, test expected Y, both plausible | **Stop.** Show both readings, ask |
| **Contract mismatch** — shape or status disagrees with the contract | **Stop always.** Either the implementation is wrong or a change request is needed |
| **Infrastructure** — DB down, missing migration, bad env | **Stop and report** |

**Attempt budget: two.** Two failed mechanical fixes means the diagnosis was
wrong; a third attempt usually makes things worse. After two, stop and show
everything tried.

Test assertion edits are hook-blocked during a fix cycle.

---

## 11. Database and migrations

### 11.1 Foundation stage

Database created, async engine + session dependency, base model
(`id`, `tenant_id`, timestamps, soft-delete flag), Alembic initialised with its
sync engine, first migration generating base tables.

### 11.2 Migration rules

- **Autogenerate, then always review the output.** Autogenerate misses
  constraint and index changes, and will happily write destructive operations.
- **Every migration has a working downgrade.**
- **Applied migrations are never edited.** *(Hook-blocked.)*
- **Partial unique indexes** for soft-deleted rows handled explicitly.
- Migrations run before tests execute.

### 11.3 In the inner loop

Model changes during `/build-endpoint` generate a migration, which is applied
before the endpoint's tests run.

---

## 12. Plan files and traceability

### 12.1 ID scheme

Stable, permanent, globally unique, never reused:

`REQ-###` requirement · `PH-#` phase · `US-###` story · `EP-###` endpoint ·
`DEC-###` decision · `Q-###` open question · `CR-###` change request ·
`ERR-###` error code

IDs are global, not per-parent, so any reference is resolvable without context.

### 12.2 Links point upward only

Each file declares its **parents**. Children are never hand-listed in parent
files.

- Endpoint declares its story and its requirements
- Story declares its phase and its requirements
- Phase declares nothing upward
- Decision declares what it affects
- Change request declares what it touched

**Why:** upward links are written once at creation and are true forever.
Downward links must be updated on every addition, and eventually one update is
missed — then Claude reads a story file, sees three endpoints, and silently
works on an incomplete set.

### 12.3 Downward views are generated

Index files — phase→stories, story→endpoints, requirement→implementations — are
built by `regen_indexes.py` from the upward declarations. **Never hand-edited.**

This gives reverse lookups for impact analysis with no possibility of drift.
A hook regenerates after any plan edit and fails if the committed index does not
match a fresh scan.

**The trick, stated plainly:** hand-written links are always upward and
immutable; generated links are always downward and disposable.

### 12.4 File contents

Each file carries a fixed **link block** at the top — machine-parseable, cheap
to read.

- **Endpoint** — ID, method + path, parent story, requirement IDs, status,
  contract path, related decisions, related questions, related error codes
- **Story** — ID, parent phase, requirement IDs, status; points at the generated
  endpoint list rather than inlining it
- **Phase** — ID, status, goal, entry/exit criteria
- **Requirement** — ID, verbatim source text, source location, status
  (active/deferred/removed), changelog of every CR that touched it
- **Decision** — ID, date, what was decided, why, alternatives rejected, what it
  affects
- **Question** — ID, what it blocks, raised date, resolution pointing at a
  decision ID

**Status lives in exactly one place per thing.** The endpoint file owns endpoint
status. Story and phase status are *derived* by `regen_indexes.py`.

### 12.5 Context discipline

Small indexes, detailed leaves, load on demand.

Building one endpoint reads: project index, that story's file, that endpoint's
file and contract, plus any questions it names. Four or five small files.

Impact analysis reads: the requirement entry, the generated reverse index, then
only the affected files.

Neither path ever loads the full source document or unrelated phases.

### 12.6 Contracts

Live in a **separate `contracts/` tree mirroring the API path structure**, not
inside story folders. Contracts are the frontend's artifact; they will be
browsed by resource, not by internal story numbering.

The endpoint file links to its contract by path.

### 12.7 Integrity check

`check_links.py`, run by a hook, verifies:

- Every referenced ID exists
- No ID appears twice
- Every active requirement is claimed by a story, or explicitly deferred
- Every endpoint belongs to a story that belongs to a phase
- Generated indexes match a fresh scan
- Nothing marked complete has unresolved questions attached
- Every toolkit cross-reference path resolves (§16.6)

A broken link is a failing check, not a surprise three weeks later.

---

## 13. Development flow

### 13.1 Outer loop — once per project

1. **Repo skeleton + tooling** — Poetry, ruff, mypy, pytest, folder structure
2. **`/ingest-requirements`** — the source document (requirements, SRS, notes,
   specs, tech requirements, all mixed) → numbered inventory → project config
   proposal → global error codes
3. **Foundation** — settings, DB engine, base model, Alembic, first migration,
   error registry + envelope + handlers, test harness
4. **Phase 0: Auth** (§7)
5. **`/plan-phases`** → **`/plan-story`**
6. **Inner loop** per story

Project choices (DB engine, roles, tenancy scope, idempotency scope) are
**findings derived from the document**, proposed by Claude and approved by the
user — not questions asked before the document is read.

### 13.2 Decomposition runs in two passes

**Pass one — inventory.** Every atomic statement extracted and given a stable
ID: functional requirements, business rules, non-functional constraints,
explicit out-of-scope notes. Anything vague goes straight to the ambiguity
register rather than being silently resolved. Output is a flat numbered list
reviewable against the source.

**Pass two — grouping.** Requirement IDs grouped into phases, then stories;
endpoints proposed per story. Every story cites the requirement IDs it
satisfies. Every requirement lands in a story or is explicitly deferred —
nothing silently disappears.

### 13.3 Inner loop — per story

1. `/plan-story` — proposes **all** endpoints for the story **as a set**, so
   their contracts are consistent with each other. User approves.
2. Contracts written; schemas authored; story-specific error codes derived
3. `test-author` writes the tests from the contracts (§10.6)
4. `/build-endpoint <story>` — works through endpoints **one at a time, fully
   complete before the next**:
   - model → migration → DAL → service → router
   - tests run at each layer; halt on failure (§10.8)
5. Next endpoint
6. `/verify-story` when all endpoints pass

**Design is upfront; building is incremental.**

### 13.4 Verification and completion

`/verify-story` checks and, if everything passes, **marks the story complete**:

- Contracts match the live OpenAPI (`contract_diff.py`)
- All tests green
- No open questions attached
- Security review clean
- Edge-case checklist walked

Status rolls up from endpoints, so `/status` reads real state rather than
something hand-maintained.

### 13.5 Live progress output

Long unsupervised runs must be observable. The build loop announces, one line
per event, prefixed with the endpoint ID:

current story and endpoint · layer being written · migration being generated ·
test file running · pass/fail counts · moving to next endpoint

Stops print what the stop is, what was done, and what is needed — not buried in
prose.

---

## 14. Change management

### 14.1 New requirement — `/new-requirement`

Lighter path, because nothing existing is affected:

1. Gets an ID in the inventory
2. User assigns it to a phase
3. Becomes a new story or extends an existing one
4. Error codes derived

No impact analysis is run, because it would find nothing. **If a "new"
requirement contradicts an existing one, the command says so and routes to
`/change-request` instead.**

### 14.2 Changed requirement — `/change-request`

1. **Trace forward** (`trace_impact.py`) from the requirement ID → stories →
   endpoints → contracts → tests
2. **Impact report**
3. **Classify each contract change:**
   - *Additive* — new optional field, new endpoint, relaxed validation. Frontend
     unaffected.
   - *Breaking* — field removed or renamed, type changed, validation tightened,
     status code changed, enum value removed.
4. **Stop for approval — always.** This is the designed decision point. Breaking
   changes get an extra question: version the endpoint, or coordinate with the
   consumer? The answer is logged with its reasoning, because in six months
   nobody remembers why `/v2` exists.
5. **On approval:** requirement changelog line · contracts updated · affected
   endpoints marked `needs-rebuild` · tests regenerated by `test-author` from
   the updated contract (same edge-case checklist, so coverage cannot silently
   narrow) · story marked incomplete · decision logged

### 14.3 Scope removal

Requirements are marked **deferred** or **removed** with a date and a reason —
never deleted. Deleting means the same argument gets relitigated in three months
with no record of how it was settled.

Endpoints already built get an explicit decision: leave, deprecate, or remove.

### 14.4 Requirement IDs are permanent

A revised source document is **diffed against the inventory** — what is new,
what changed, what disappeared — reviewed, and applied as change requests.

**Decomposition is never re-run**, because renumbering would break every trace
link.

Phase re-planning is separate and rare: `/plan-phases` can regroup existing
stories without touching requirement IDs or contracts.

### 14.5 Contracts are the source of truth

If code and contract disagree, that is a bug. `contract_diff.py` compares the
live OpenAPI output against the committed contracts. Without this check,
contracts rot within a month and become documentation nobody trusts.

---

## 15. Ambiguity protocol and stop conditions

### 15.1 Where ambiguity is resolved

Concentrated at the **contract stage**, where it is cheap. By the time an
endpoint is being built, the contract plus conventions should have pre-answered
almost everything.

Applied literally during the build, "stop on any ambiguity" causes stop-fatigue
and gets switched off within a week. So the build-time rule is narrow:

| Situation | Action |
|---|---|
| Not covered by contract or conventions, **and it changes behaviour** | **Stop and ask** |
| Not covered, purely cosmetic | Follow conventions, note it, continue |
| **Contradicts the contract** | **Stop, always** |

Open questions are **written to `plan/questions.md`**, not merely spoken, so they
survive context compaction.

### 15.2 Automatic stop conditions

Inside a running command, Claude halts without being asked on:

- Behaviour-changing ambiguity not covered by contract or conventions
- Contract mismatch
- Logic-class test failure (§10.8)
- Breaking change detected during a change request
- New dependency needed
- Two failed fix attempts
- Infrastructure failure

Everything else runs through: layers, mechanical fixes, formatting, index
regeneration.

### 15.3 State lives in files, not conversation

Phases, stories, contracts, decisions, open questions, endpoint status — all
files. A session gets compacted or a terminal closes, and anything that existed
only in chat is gone.

This also makes every command resumable: `/build-endpoint US-003` works whether
or not it is the session that designed the contract.

---

## 16. Toolkit composition

### 16.1 Primitives — how to decide

| Question | Primitive |
|---|---|
| Must happen every time, zero judgment? | **Hook** (calling a **script**) |
| Knowledge about *how* we do something? | **Skill** |
| A stage you start by typing? | **Command** |
| Needs its own context window or fewer permissions? | **Subagent** |
| Deterministic logic something else calls? | **Script** |
| A blanket allow/deny? | **settings.json** |
| True in every session, cheap to always load? | **CLAUDE.md** |

**Tools are not authored.** Claude Code's tools are built in; the only way to add
one is an MCP server. Not needed for v1 — a Postgres MCP server is the only
candidate worth revisiting later.

**Agents and subagents are the same thing.**

### 16.2 Skills — 13

| Skill | Covers |
|---|---|
| `layered-architecture` | Layers, responsibilities, build order |
| `dal-conventions` | Tenant filter, soft delete, cursor pagination, async rules |
| `service-conventions` | Business logic, error raising, injected sessions, transactions |
| `router-conventions` | Thin routers, dependency wiring, status codes |
| `auth-module-build` | Phase 0 sequence, two-token model, membership, cookies/CSRF |
| `auth-security-checklist` | The PyJWT traps. Short, invariant |
| `testing-strategy` | What is tested where, fixtures, token factory, rollback isolation |
| `edge-case-checklist` | The category walk |
| `error-registry` | How errors are defined, derived, and raised |
| `alembic-migrations` | Autogenerate review, downgrades, partial unique indexes |
| `plan-file-format` | IDs, upward links, file shapes |
| `requirement-decomposition` | Doc → inventory → phases → stories |
| `contract-authoring` | Contract contents, additive vs breaking classification |

### 16.3 Commands — 12

| Command | Purpose |
|---|---|
| `/ingest-requirements` | Doc → inventory + project config + global error codes |
| `/plan-phases` | Group requirements into phases |
| `/plan-story` | Story + its full endpoint set + contracts + error codes |
| `/build-endpoint` | Takes a story, builds endpoints one at a time |
| `/verify-story` | Full check; marks story complete |
| `/change-request` | Impact analysis → approval → updates |
| `/new-requirement` | Lighter path for additions |
| `/security-review` | On-demand |
| `/status` | Project state |
| `/toolkit-status` | Toolkit sync state |
| `/update-toolkit` | `git pull` inside `.claude/` |
| `/promote-to-toolkit` | Commit + push to toolkit main |

`/status` and `/toolkit-status` are **separate** — different questions, and
merging them makes `/status` too noisy to run constantly.

`/add-error-code` exists but is the exception path (§9.4).

### 16.4 Subagents — 3

| Subagent | Permissions | Why it is a subagent |
|---|---|---|
| `requirements-analyst` | read-heavy | Keeps the giant source document out of the main context |
| `test-author` | writes only to `tests/` | Writes from the contract without implementation details leaking in |
| `security-reviewer` | **read-only** | Read-only is a real guarantee, not a suggestion |

**Security review triggers** (not per endpoint — most endpoints are plumbing):
1. **Any change under `app/auth/`** — always, no exceptions
2. **End of story**, at `/verify-story` — reviews the whole story diff, catching
   cross-cutting mistakes at roughly a fifth the cost of per-endpoint runs
3. **Manual** via `/security-review`

*Accepted tradeoff:* a bad pattern can be repeated across three endpoints before
story-end review catches it. The fix is mechanical once spotted; auth code is
covered by trigger 1.

### 16.5 Hooks — 7

| Hook | Event | Action |
|---|---|---|
| `guard_env` | PreToolUse | Block read/write of `.env`, `.env.*` (except `.env.example`) |
| `guard_pip` | PreToolUse (Bash) | Block `pip install` → use `poetry add` |
| `guard_bash` | PreToolUse (Bash) | Block `git push`, `dropdb`, destructive `rm` |
| `guard_test_db` | PreToolUse | Block `TRUNCATE`/`DROP`/`drop_all` in `tests/`; block edits to applied migrations |
| `fmt_lint_type` | PostToolUse (`*.py`) | ruff format, ruff check --fix, mypy — **edited file only** |
| `on_plan_edit` | PostToolUse (`plan/*`) | `regen_indexes.py` + `check_links.py` |
| `on_dal_edit` | PostToolUse (`app/dal/*`) | `dal_guard.py` |

**Scoping matters:** `fmt_lint_type` touches only the edited file. Pre-existing
errors elsewhere never block — otherwise one legacy module makes the toolkit
unusable.

**Deliberately not hooks:** the full test suite (too slow — that is a command),
and anything requiring judgment (that is a subagent).

**Deferred:** a Stop hook blocking turn-end on incomplete work. Good idea,
annoying until the rest is proven.

**Verify before relying on:** a hook runs a shell command, so it cannot directly
launch a subagent. Auto security review on auth changes works by the hook
emitting an instruction for Claude to run the reviewer. Confirm the current hook
output contract in the Claude Code docs.

### 16.6 Scripts — 6

| Script | Purpose |
|---|---|
| `id_allocator.py` | Issues the next ID of any type. Atomic — no duplicates |
| `regen_indexes.py` | Rebuilds downward views; rolls status up |
| `check_links.py` | ID integrity + toolkit cross-reference integrity |
| `trace_impact.py` | Requirement → stories → endpoints → contracts → tests |
| `contract_diff.py` | Live OpenAPI vs committed contracts |
| `dal_guard.py` | Tenant filter, soft-delete filter, tenant-from-input, `os.getenv` outside settings, blocking calls in async |

`.env.example` parity and import-vs-declared checks fold into existing hooks.

### 16.7 Cross-referencing — invariant

**Every reference is a repo-relative path, never a bare name.** Not "run the
integrity check" — the actual path.

- Commands name the skills they load and the scripts they call, by path
- Skills name the scripts, templates, and other skills they depend on, by path
- Hooks name the script they execute, by path
- Subagents name the skills they operate under, by path
- Scripts carry a header noting which hooks and commands call them

Each file carries a short **references block** near the top — reads / writes /
calls / called-by — so the dependency graph is readable without opening
everything.

`check_links.py` verifies: every referenced path exists, every script has at
least one caller, nothing points at a renamed file. `/promote-to-toolkit` runs
this before pushing — pushing a skill that references a script you did not push
breaks the toolkit for every future project.

### 16.8 Poetry discipline — invariant

- Every dependency enters via `poetry add` / `poetry add --group dev`. Never
  `pip install`, never a hand-edited `pyproject.toml`
- Everything runs through `poetry run`
- `poetry.lock` is committed; regenerated on any dependency change
- Every top-level import in `app/` resolves to a declared dependency
- **A new dependency is a stop-and-ask moment** — not a blocker, but it is
  announced, not silent

### 16.9 `.env` discipline — invariant

- **Claude never reads `.env`.** Permission deny list, not a prose request
- **`.env.example` is the contract.** Committed, every key present, placeholders
  only. A new setting means editing `.env.example` and telling the user to fill
  the real value
- **One typed settings class** (pydantic-settings), loaded once. No `os.getenv`
  scattered through the codebase — that is what makes a project impossible to
  configure for a new environment
- `.env.test` (if ever needed) is gitignored
- Secrets never appear in contracts, stories, or decision logs — those are
  committed

---

## 17. Deliberately deferred

| Item | Why | Revisit when |
|---|---|---|
| `infra/` folder | No conventions to evaluate invented structure against | Deployment is actually attempted |
| Docker | Not blocking anything | Identical DB versions across machines matter |
| Separate test database | Transaction rollback is sufficient | Commit-dependent behaviour needs testing |
| JWKS endpoint | Nothing validates tokens except the issuing service | A second service validates tokens |
| Key rotation tooling | `kid` support exists; the procedure can wait | A key is actually old |
| MFA, password reset | Slot into login without touching tokens or schema | A buyer asks |
| PKCE, discovery, consent, client registration | Serve third-party clients that do not exist | Third-party clients exist |
| SSO federation | No tenant needs it | A tenant needs it |
| Per-tenant audit with field history | Middleware audit covers platform admin | A tenant asks |
| Stop hook | Annoying before the core loop is proven | Drift actually happens |
| MCP servers | Scripts via Bash cover current needs | A Postgres MCP server would pay for itself |
| `test-author` reviewing regenerated tests | Checklist prevents silent narrowing | Coverage is observed to drop |

---

## 18. Build order for the toolkit

**Insurance first** — `docs/design-spec.md`, `docs/decisions.md`, `README.md`.
After these, the originating conversation is expendable.

**Then the thin slice** — enough to run one endpoint end to end:

`CLAUDE-base.md` · `settings.json` · `layered-architecture` · `dal-conventions` ·
`service-conventions` · `router-conventions` · `testing-strategy` ·
`plan-file-format` · `/build-endpoint` · `id_allocator.py` · `check_links.py` ·
`fmt_lint_type` hook

**Then prove it** on one real endpoint in a throwaway project, start to finish.
Expect to find three or four wrong assumptions. Fix them in the toolkit, push,
continue.

**Then everything else**, in any order.

**Do not build all 13 skills before trying anything.** Building the whole
toolkit around an untested assumption is the expensive failure mode.

### 18.1 Within the toolkit, build in this order

Scripts and hooks → CLAUDE.md and settings → skills → commands → subagents.

Scripts and hooks first because they are what make everything else trustworthy.

---

## 19. Amendment log

| Date | Change | Reason |
|---|---|---|
| — | Initial specification | — |
