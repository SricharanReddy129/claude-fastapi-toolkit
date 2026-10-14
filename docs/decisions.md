# Toolkit Decisions

**Purpose:** Why each default is the default. Lets a future reader tell an
arbitrary choice from a considered one, and shows what was already rejected so
the same argument is not relitigated.

**Scope:** Toolkit-level decisions, IDs prefixed `TD-`. These are distinct from
per-project decisions, which use `DEC-###` and live in `plan/decisions.md`.

**Rules:**
- A decision is amended, never silently rewritten. Add a row to §Amendments.
- Tier meanings are in `docs/design-spec.md` §3.
- "Override cost" states what it takes to go the other way in one project.

---

## Architecture

### TD-001 — Layered architecture: api / schemas / services / dal / models
**Tier:** invariant (the layering), default (sub-folder organisation)

**Decision:** Five layers, business logic confined to `services/`.

**Rationale:** Matches the structure already in use. Confining logic to one
layer is what makes the DAL mechanically checkable (`dal_guard.py`) and what
makes service unit tests meaningful.

**Rejected:** Logic in routers (untestable without HTTP), logic in the DAL
(makes tenant-filter checking unreliable because queries stop being uniform).

**Override cost:** High. Most skills assume this split.

---

### TD-002 — Build bottom-up: model → DAL → service → router
**Tier:** default

**Decision:** Schemas at contract approval, then bottom-up through the layers.

**Rationale:** Every layer is written against something real. Mocks are needed
only at the service-test boundary.

**Rejected:** Top-down. Every layer below is a mock that gets thrown away as the
real layer lands — pure churn.

**Rejected:** Outside-in TDD (failing API test first, build down to green). A
legitimate approach, and it fits contract-first thinking, but it is redundant
here: tests are already authored from the contract before implementation
(TD-020), which achieves the same discipline without the mock scaffolding.

**Override cost:** Low. A project can reverse the order; the skills describe
layers independently.

---

### TD-003 — Async SQLAlchemy as default
**Tier:** default

**Decision:** Async for the application, sync for Alembic.

**Rationale:** Real concurrency benefit under slow I/O, which these projects
have (LLM and third-party adapters).

**Explicitly not the rationale:** that async "acts as sync when there is no
latency." That framing is wrong — async is a different execution model with
real costs, not a free superset. The costs are listed in design-spec §5.3 and
are accepted knowingly.

**Rejected:** Sync throughout. Simpler, and defensible for a CRUD-only project —
but the adapter layer makes concurrency under slow I/O likely in most projects.

**Override cost:** High once built. Low at project start — this is a reasonable
thing to decide per project.

---

## Multi-tenancy

### TD-004 — Identity global, authorization per membership
**Tier:** invariant

**Decision:** Three tables — `users` (no tenant), `memberships` (user × tenant,
carrying roles), everything else tenant-scoped.

**Rationale:** A user belongs to multiple tenants, with different roles in each.
Roles on the user record cannot express that.

**Rejected:** Tenant column on `users`. Forces duplicate accounts per tenant and
breaks global email uniqueness.

**Override cost:** Very high. This is a schema decision; changing it later is a
migration of everything.

---

### TD-005 — Tenant isolation enforced at the DAL, not middleware
**Tier:** invariant

**Decision:** Every query against a tenant-scoped table filters on tenant.
`tenant_id` comes from the validated token context only.

**Rationale:** Middleware cannot know what `invoice_id=4471` refers to — record
ownership is only knowable after the query. Middleware handles authentication
and route-level RBAC; record-level isolation is a data concern.

**Rejected:** Trusting a tenant header or body field. If a client can send it, a
client can change it.

**Override cost:** None — this is not overridable.

---

### TD-006 — Cross-tenant access returns 404, not 403
**Tier:** default (but changing it is strongly discouraged)

**Decision:** 404.

**Rationale:** 403 confirms the record exists, which leaks existence across
tenant boundaries.

**Rejected:** 403. Clearer for debugging, worse for isolation.

**Override cost:** Low mechanically, high in consequence. Log the reasoning if
overridden.

---

## Authentication

### TD-007 — First-party auth, not an OpenID Provider
**Tier:** choice, settled for current projects

**Decision:** Self-issued OIDC-shaped tokens for our own frontend. No client
registration, consent screens, authorization code flow, PKCE, or discovery.

**Rationale:** Those features exist to serve third-party clients, which do not
exist. Building them is roughly five times the work for zero current benefit.

**Revisit when:** A third-party client or SSO federation is actually required.

---

### TD-008 — Two token types: identity and access
**Tier:** invariant

**Decision:** Identity token (no tenant, can only list tenants and exchange),
access token (one tenant + roles in that tenant). A `typ` claim distinguishes
them and is validated.

**Rationale:** Follows directly from TD-005. Tenant must be inside the signed
token, so switching tenants requires proving membership again.

**Rejected:** One token listing all memberships, with an active-tenant header.
Tenant would then arrive from user input — the exact failure TD-005 prevents.

**Accepted cost:** One extra round trip after login.

---

### TD-009 — Asymmetric keys with `kid`, not HS256
**Tier:** default

**Decision:** Asymmetric, `kid` in the header from day one.

**Rationale:** HS256 is defensible for a single service that both issues and
validates. But `kid` is what makes rotation possible without changing the token
format — roughly an hour of extra work now versus a migration later.

**Rejected:** HS256. Simpler, and would need replacing the day a second service
validates tokens or a key needs rotating.

---

### TD-010 — 15-minute access tokens + refresh tokens
**Tier:** default

**Decision:** Short-lived access tokens, refresh tokens for continuity.

**Rationale:** This is the decision that makes complex revocation machinery
unnecessary. A user removed from a tenant is locked out within 15 minutes
automatically, with no denylist and no per-request DB lookup.

**Rejected:** Long-lived access tokens plus a revocation list. Trades a simple
expiry policy for a per-request lookup and a distributed-state problem.

**Rejected:** Long-lived tokens with a membership-version claim checked per
request. Workable, costs a lookup on every request.

---

### TD-011 — Refresh rotation with reuse detection, in v1
**Tier:** invariant (once chosen)

**Decision:** Each refresh issues a new token and invalidates the old. Reuse of
a spent token revokes the whole family.

**Rationale:** Retrofitting is painful not because the code is hard but because
it changes client behaviour — clients built against non-rotating refresh tokens
break when rotation is added.

**Known wrinkle:** Concurrent refreshes (multiple tabs, retrying mobile client)
can trip reuse detection and log the user out spuriously. Mitigated by a short
grace window where a just-rotated token is still accepted. This must be designed
in, not discovered.

---

### TD-012 — Refresh token in httpOnly cookie; access token in response body
**Tier:** default

**Decision:** Refresh in `HttpOnly; Secure; SameSite=None; Path=<refresh path>`
cookie. Access token in the response body, held in frontend memory, sent as a
bearer header.

**Rationale:** Cookie protects the refresh token from XSS. Frontend is
cross-origin, so `SameSite=Strict` is unavailable — which makes CSRF validation
on the refresh endpoint **mandatory and part of Phase 0**, not optional.

**Rejected:** Refresh token in the response body. Simpler, no CSRF concern, but
exposes the longest-lived credential to XSS.

**Rejected:** Access token in a cookie as well. Mixing both makes every endpoint
CSRF-exposed rather than just the refresh endpoint.

**Open:** Non-browser clients (mobile, server-to-server) cannot use cookies
naturally. If they appear, the refresh endpoint needs a body-based variant gated
by client type.

---

### TD-013 — argon2 for password storage
**Tier:** default

**Rationale:** Current recommended default. bcrypt is an acceptable alternative.

---

### TD-014 — PyJWT
**Tier:** default

**Decision:** PyJWT, with the four traps in design-spec §7.7 treated as
invariants and checked by `security-reviewer`.

**Rationale:** Already familiar, maintained, standard. Writing the protocol is
defensible; writing the crypto is not.

---

## Data access

### TD-015 — Cursor pagination
**Tier:** default

**Decision:** Signed opaque cursor encoding sort field plus a tiebreaker.
Ordering must be on an immutable column.

**Rationale:** Stable under concurrent inserts, which offset pagination is not.
Signing prevents a client forging a cursor into another tenant's range.

**Rejected:** Offset/limit. Simpler, and fine for small admin lists — but
silently skips or duplicates rows when the underlying set changes between pages.

---

### TD-016 — Soft delete
**Tier:** choice (which tables), invariant (filtering, where applied)

**Decision:** Soft delete on tenant-scoped tables by default; the exact set is a
per-project finding.

**Consequence:** A second mandatory DAL filter, same failure class as the tenant
filter — forget it once and deleted records reappear.

**Per-project decisions:** 404 or 410 for a soft-deleted record; whether a
unique value is re-usable after deletion (usually needs a partial unique index).

---

### TD-017 — Idempotency keys on POST and non-idempotent PATCH
**Tier:** choice (scope), invariant (semantics)

**Decision:** Stored key table. Same key + same request returns the stored
response; same key + different request is a 409; the key is captured before
processing.

**Rationale:** The domain involves financial operations where double submission
has real consequences.

---

### TD-018 — Audit via middleware, platform-admin only
**Tier:** default

**Decision:** Middleware-level request/response audit for platform admin.

**Stated limitation, accepted knowingly:** middleware sees the request and the
response, not the before/after of a row. Field-level history is a DAL-level
concern and a different mechanism.

**Revisit when:** A tenant requires their own audit trail.

---

### TD-019 — Services take an injected session and never commit
**Tier:** invariant

**Rationale:** Two independent reasons. It is what makes a multi-step operation
atomic. And it is what keeps the test transaction in control (TD-022) — a
service that commits internally escapes the rollback and writes to real data.

---

## Testing

### TD-020 — Tests authored upfront from the contract, by a subagent
**Tier:** default

**Decision:** `test-author` writes the suite from the approved contract before
implementation. `/build-endpoint` runs against a red suite and is done when
green.

**Rationale:** A test written after seeing the implementation tends to test what
the code does rather than what the contract promised. A separate context keeps
implementation details out.

**Rejected:** Writing tests during the build. Faster per endpoint, but the tests
drift toward describing the implementation.

---

### TD-021 — Reduced test matrix
**Tier:** default

**Decision:** Service unit tests on meaningful branches, one integration test
per endpoint through the real stack, contract assertions, DAL tests per
non-trivial query.

**Rejected:** Unit + integration at every layer per endpoint. Two reasons.
"Integration testing per layer" is not a coherent category — integration happens
*between* layers, and a service tested against a mocked DAL is still a unit test
with a fancier mock. And unit-testing a router in isolation asserts that a mock
was called with arguments you chose; it passes forever and catches nothing.

**Compensating control:** The edge-case checklist (design-spec §10.7), walked per
endpoint with N/A recorded, so reduced count does not mean reduced thought.

---

### TD-022 — One database, transaction rollback for isolation
**Tier:** default

**Decision:** Dev and test share a database. The session fixture opens a
transaction and rolls it back unconditionally. No test commits, no test
truncates or drops, tests create their own data.

**Rationale:** User constraint — no second database, no Docker. The transaction
pattern provides genuine isolation without either.

**Rejected:** Separate `_test` database. Safer by default and the usual
recommendation, but rejected in favour of the simpler operational setup. The
rollback pattern is sufficient given TD-019.

**Known limitation:** Anything genuinely requiring a commit — real concurrency
behaviour — cannot be tested this way.

**Revisit when:** Commit-dependent behaviour needs testing. The change is one
`CREATE DATABASE`.

---

### TD-023 — Token factory, never an auth bypass flag
**Tier:** invariant

**Decision:** Tests mint real signed tokens via a fixture taking tenant and
roles.

**Rejected:** A config flag disabling auth in test mode. It makes tests easy and
eventually ships to production. The factory gives the same convenience while
exercising the real middleware on every request — which matters, because that
middleware is the only thing standing between tenants.

---

### TD-024 — Claude fixes code, never tests, without asking
**Tier:** invariant

**Decision:** Failures are classified before anything is touched (design-spec
§10.8). Mechanical failures are fixed silently; logic, contract-mismatch, and
infrastructure failures stop. Attempt budget: two.

**Rationale:** A test encodes the approved contract. A suite edited into passing
is worse than a red suite, because it looks green.

**Why two attempts:** Two failed mechanical fixes means the diagnosis was wrong,
and a third attempt is typically where things get worse rather than better.

---

## Process

### TD-025 — Upward links only; downward views generated
**Tier:** invariant

**Decision:** Each plan file declares its parents. Child lists are generated by
`regen_indexes.py` and never hand-edited.

**Rationale:** Upward links are written once at creation and stay true. Downward
links need updating on every addition, and one missed update means Claude reads
a story file, sees three endpoints, and silently works on an incomplete set.

---

### TD-026 — Requirement IDs are permanent
**Tier:** invariant

**Decision:** Decomposition runs once. A revised source document is diffed
against the inventory and applied as change requests.

**Rationale:** Re-running decomposition renumbers requirements and breaks every
trace link in the project.

---

### TD-027 — Ambiguity resolved at the contract stage, not during the build
**Tier:** default

**Decision:** Build-time stops are narrow — behaviour-changing gaps and contract
contradictions only. Cosmetic gaps follow conventions and are noted.

**Rationale:** "Stop on any ambiguity" applied literally during a build produces
stop-fatigue, and a tool that interrupts constantly gets switched off within a
week. Concentrating resolution at the contract stage makes stops rare and
meaningful.

---

### TD-028 — Security review at story end, not per endpoint
**Tier:** default

**Decision:** Three triggers — any change under `app/auth/` (always), end of
story, and manual.

**Rationale:** Most endpoints are plumbing; per-endpoint review mostly burns
tokens confirming nothing changed. Story-end review catches cross-cutting
mistakes at roughly a fifth the cost.

**Accepted tradeoff:** A bad pattern can be repeated across three endpoints
before it is caught. The fix is mechanical once spotted, and auth code — where a
silent bug is worst — is covered by the always-on trigger.

---

### TD-029 — Endpoints designed as a set, built one at a time
**Tier:** default

**Decision:** `/plan-story` proposes all endpoints for the story together;
`/build-endpoint` completes them one at a time.

**Rationale:** Contracts within a story must be consistent with each other, so
they are designed together. Building vertically one endpoint at a time keeps
each unit small enough to hold in context and ends in a state where something
runs.

**Rejected:** Discovering endpoints as you build. Produces inconsistent
contracts within a story and gives the frontend a moving target.

**Rejected:** Building horizontally (all routers, then all services). A bad
decision propagates across the whole story before anything is testable.

---

### TD-030 — Toolkit lives per project, not per device
**Tier:** invariant

**Decision:** The toolkit is cloned into `project/.claude/` and edited there.
`/promote-to-toolkit` pushes from inside `.claude/` directly to `main`.

**Rationale:** User constraint, and it removes the copy-down step entirely — the
project is on the promoted commit because it *is* that commit. No drift window.

**Rejected:** A permanent machine-level clone with copy-on-init. Standard
approach, but creates a window where the project's copy and the toolkit disagree.

**Consequence:** The hook blocking edits inside `.claude/` cannot exist. Its
replacement is visibility — `/toolkit-status` reports uncommitted changes there,
because an edit that is neither promoted nor moved to overrides is an undecided
state.

---

### TD-031 — Push promotions straight to `main`
**Tier:** default

**Decision:** No review branch.

**Rationale:** Single user, and ceremony that is not needed gets skipped anyway.

**Accepted risk:** A half-formed idea becomes the template for every future
project immediately. Mitigated by `check_links.py` running before the push.

---

### TD-032 — Three convention tiers with no override switch for invariants
**Tier:** invariant

**Decision:** Invariants have no config flag.

**Rationale:** A switch that exists will eventually be flipped at 11pm, and the
invariants are the rules whose violation is a security or data-integrity bug
rather than a style difference.

---

### TD-033 — Error codes derived during planning, not added ad hoc
**Tier:** default

**Decision:** Global codes from `/ingest-requirements`; story codes from
`/plan-story`. `/add-error-code` exists as the exception path.

**Rationale:** Codes then exist before the code that raises them, so the service
layer references a registry entry rather than inventing a string. Also forces
every violable business rule to be identified during planning.

---

### TD-034 — No MCP servers in v1
**Tier:** default

**Rationale:** Everything needed is a script invoked via Bash. Adding an MCP
server adds a moving part with no current payoff.

**Revisit when:** A Postgres MCP server would meaningfully beat running queries
through scripts.

---

### TD-035 — Thin slice before full build
**Tier:** default

**Decision:** Build enough to run one endpoint end to end, prove it on a
throwaway project, then fill in the rest.

**Rationale:** Building 13 skills around an untested assumption is the expensive
failure mode. Expect three or four wrong assumptions on first contact.

---

## Amendments

| Date | Decision | Change | Reason |
|---|---|---|---|
| — | — | Initial set | — |
