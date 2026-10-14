# Skill: testing-strategy

**Tier:** invariant (isolation rules, token factory, fix policy) ·
default (matrix, authoring)
**Read when:** writing tests, setting up fixtures, or handling a test failure.

**References**
- Reads: `.claude/docs/design-spec.md` §10 ·
  `.claude/docs/decisions.md` TD-020…TD-024 ·
  `conventions.override.md` → section `testing-strategy`
- Related: `.claude/skills/edge-case-checklist.md` (**walk it every endpoint**),
  `.claude/skills/service-conventions.md`,
  `.claude/skills/contract-authoring.md`
- Called by: `.claude/commands/build-endpoint.md`,
  `.claude/commands/verify-story.md`
- Written by: `agents/test-author.md`

---

## What is tested, per endpoint

| Target | Scope |
|---|---|
| **Service unit tests** | One per meaningful branch — authz rule, validation rejection, state transition, edge case. This is where logic lives, so this is where mocks earn their keep |
| **Utils and validators** | Where real logic exists |
| **One integration test per endpoint** | Through the real stack — happy path plus the failures that matter. This catches wiring bugs, and wiring is where FastAPI projects break |
| **Contract assertions** | Response shape and status match the committed contract |
| **DAL** | Per non-trivial query, not per endpoint |

**Not tested:** routers in isolation (asserting a mock was called with arguments
you chose), DAL plumbing with no logic, Pydantic doing what Pydantic does.

Reasoning for the reduced matrix: `docs/decisions.md` TD-021.

---

## Auth testing

Because auth and RBAC live in middleware, endpoints are free of that duty.

**Tested once, deeply — the middleware.** Missing token, malformed, expired,
wrong signature, wrong issuer, wrong audience, wrong algorithm, tampered
payload, valid-but-revoked, wrong `typ`, every role against every permission in
the matrix. One investment, covers every endpoint forever.

**Tested per endpoint — exactly two things:**

1. **Role binding** — one allowed role passes, one disallowed role gets 403.
   Catches the realistic bug: a route annotated with the wrong permission.
2. **Cross-tenant returns 404** — valid token for tenant A requesting tenant B's
   record. **Mandatory on every endpoint touching tenant data, no exceptions.**
   This is the test that catches a missing DAL filter.

The permission matrix generates the middleware permission tests, so adding a
role expands coverage automatically.

---

## Token factory *(invariant)*

A fixture mints a real signed token for any tenant and role combination, in one
line. Cross-tenant tests become trivial.

**Never a config flag that disables auth in test mode.** It makes tests easy and
eventually ships to production. The factory gives the same convenience while
exercising the real middleware on every single request — which matters, because
that middleware is the only thing standing between tenants.

---

## Database isolation — one database *(invariant rules)*

Dev and test share a database. Isolation comes from transactions.

The session fixture opens a transaction, the test runs, the transaction is
**rolled back unconditionally**. Nothing is ever committed, so dev data is
untouched — tests cannot see it and cannot modify it.

**Three rules make this hold:**

1. **No test commits.** The fixture owns the transaction; test code never calls
   commit. This is why services take an injected session
   (`service-conventions`) — a service that commits internally escapes the
   rollback and writes to real data.
2. **No test truncates or drops.** `TRUNCATE`, `DROP`, `metadata.drop_all` are
   hook-blocked in `tests/`.
3. **Tests create their own data** inside the transaction and assume nothing
   pre-exists. No reliance on seed rows.

A fixture asserts the database URL matches what the test config declares, so a
misconfigured run fails loudly rather than operating on something unexpected.

**Known limitation:** anything genuinely requiring a commit — real concurrency
behaviour — cannot be tested this way. Revisit per `docs/decisions.md` TD-022.

---

## Tests are written before implementation *(default)*

`test-author` writes the suite **from the approved contract**, before the build
starts. `/build-endpoint` runs against a red suite and is done when it is green.

**Why:** a test written after seeing the implementation tends to test what the
code does rather than what the contract promised. A separate context keeps
implementation details out.

When a change request updates a contract, `test-author` regenerates the affected
tests from the updated contract, walking the same edge-case checklist — so
coverage cannot silently narrow.

---

## Edge-case coverage

`.claude/skills/edge-case-checklist.md` is walked for **every** endpoint. The
test file records which categories were considered and which are N/A.

Most endpoints mark half of them N/A. The value is that the question was asked —
"did we cover enough" gets an auditable answer rather than depending on how
thorough the session felt.

---

## Test failure handling *(invariant)*

**Claude fixes code. Claude never fixes a test without asking.** A test encodes
the approved contract; a suite edited into passing is worse than a red suite,
because it looks green.

**Classify before touching anything:**

| Class | Signal | Action |
|---|---|---|
| **Mechanical** | Import error, typo, wrong fixture name, missing await, signature mismatch | Fix, note in the summary |
| **Logic** | Code does X, test expected Y, both plausible | **Stop.** Show both readings, ask |
| **Contract mismatch** | Shape or status disagrees with the contract | **Stop always.** Either the implementation is wrong or a change request is needed |
| **Infrastructure** | DB down, missing migration, bad env | **Stop and report** |

**Attempt budget: two.** Two failed mechanical fixes means the diagnosis was
wrong, and a third attempt is typically where things get worse. After two, stop
with everything tried.

Test assertion edits are hook-blocked during a fix cycle. If a test is genuinely
wrong, propose the change and wait for approval.

---

## Fixtures

Expected set, in roughly this order of dependency:

- Engine and session, with the rollback transaction
- Test client bound to that session
- Token factory
- Tenant and user builders
- Per-resource builders creating minimal valid records

Builders take overrides so a test can vary one field without restating the rest.
A test that needs ten lines of setup usually wants a builder that does not exist
yet.

---

## Structure and naming

`tests/` mirrors the layer structure. Test names state the behaviour and the
expectation, not the function name — a failing test should be readable as a
sentence about what broke.

One assertion concept per test. A test asserting five unrelated things reports
one failure and hides four.

---

## Common violations

| Symptom | Fix |
|---|---|
| `session.commit()` in a test | Remove — the fixture owns the transaction |
| Test truncates tables to clean up | Rollback already handles it |
| Test depends on seed data | Create what it needs |
| Auth disabled or mocked out | Token factory |
| Router unit-tested with a mocked service | Delete it; the integration test covers this |
| Cross-tenant test missing on a tenant-scoped endpoint | Add it — mandatory |
| Test edited to match the implementation | **Stop** — that is a contract conversation |
| Edge-case categories not recorded | Walk the checklist, record N/A explicitly |

---

## Overrides

Check `conventions.override.md` → section `testing-strategy` for matrix and
authoring choices.

Isolation rules, the token factory, and the fix policy are **invariant**.
