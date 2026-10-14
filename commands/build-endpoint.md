---
description: Build a story's endpoints one at a time, bottom-up, running tests at each layer.
argument-hint: <US-###> | <EP-###>
---

# /build-endpoint

The workhorse. Takes a story and completes its endpoints **one at a time**,
fully, in sequence.

**Loads**
- `.claude/skills/layered-architecture.md`
- `.claude/skills/dal-conventions.md`
- `.claude/skills/service-conventions.md`
- `.claude/skills/router-conventions.md`
- `.claude/skills/alembic-migrations.md`
- `.claude/skills/testing-strategy.md`
- `.claude/skills/error-registry.md`

Also loads `.claude/skills/auth-module-build.md` and
`.claude/skills/auth-security-checklist.md` when touching `app/auth/`.

**Calls:** `.claude/scripts/contract_diff.py`,
`.claude/scripts/regen_indexes.py`

---

## Input

`$ARGUMENTS` — a `US-###` (works through its endpoints) or a single `EP-###`
(rebuild one).

Reads only: `plan/index.md`, the story file, the endpoint file, its contract,
attached questions. **Never** the source document or unrelated phases.

---

## Preconditions

Per endpoint: contract exists, schemas exist, tests exist and are red, no
blocking `Q-###`.

Missing any of these means `/plan-story` has not run. Stop and say so.

---

## Per-endpoint sequence

Announce each step — one line, prefixed with the `EP-###`.

1. **Model** — table, relationships, tenant column, soft-delete flag
2. **Migration** — autogenerate, **review line by line**, apply, test the
   downgrade
3. **DAL** — tenant filter, soft-delete filter, cursor pagination. Run DAL tests
4. **Service** — business logic, registry errors, injected session. Run service
   unit tests
5. **Router** — thin, permission-bound, response model. Run integration and
   contract tests
6. **Contract check** — `contract_diff.py`. Any drift is a stop
7. **Mark** the endpoint `done`, run `regen_indexes.py`, move to the next

No pause between layers when things pass. Halt immediately when they do not.

---

## Test failure handling

Classify before touching anything:

| Class | Action |
|---|---|
| Mechanical — import, typo, fixture name, missing await, signature | Fix, note it |
| Logic — both readings plausible | **Stop.** Show both, ask |
| Contract mismatch | **Stop always** |
| Infrastructure — DB down, missing migration, bad env | **Stop and report** |

**Budget: two attempts**, then stop with everything tried.

**Fix code, never tests, without asking.** A test encodes the approved contract.

---

## Progress output

One line per event, prefixed with the endpoint ID: current endpoint, layer being
written, migration generated, test file running, pass/fail counts, moving on.

No paragraphs between steps.

---

## Stop conditions

- Behaviour-changing ambiguity not covered by contract or conventions
- Anything contradicting the contract
- Logic-class test failure
- New dependency needed
- Two failed fix attempts
- Infrastructure failure
- Missing precondition

**Do not stop** for cosmetic gaps — follow conventions, note it, continue.

Write every stop to `plan/questions.md` before reporting.

---

## Do not

- Build horizontally — all DALs, then all services
- Batch migrations to the end of the story
- Edit a test to make it pass
- Add a dependency silently
- Invent an error code
- Mark an endpoint done with failing tests or contract drift
- Continue to the next endpoint after a stop

---

## Next

`/verify-story <US-###>` once every endpoint is done.
