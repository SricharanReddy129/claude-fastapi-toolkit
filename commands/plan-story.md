---
description: Design a story's full endpoint set, write contracts and schemas, derive error codes, and author tests.
argument-hint: <US-###>
---

# /plan-story

Designs **all** endpoints for one story as a consistent set, then produces
contracts, schemas, error codes, and tests — before any implementation.

**Loads**
- `.claude/skills/contract-authoring.md`
- `.claude/skills/plan-file-format.md`
- `.claude/skills/error-registry.md`
- `.claude/skills/router-conventions.md` (paths, status codes)
- `.claude/skills/edge-case-checklist.md`

**Delegates to:** `.claude/agents/test-author.md`
**Calls:** `.claude/scripts/id_allocator.py`,
`.claude/scripts/regen_indexes.py`, `.claude/scripts/check_links.py`

---

## Input

`$ARGUMENTS` — a `US-###`. If omitted, show incomplete stories in the current
phase and ask.

---

## Steps

**1. Read** the story file, its requirement entries, `plan/project-config.md`,
and any `Q-###` attached. Nothing else.

**2. Propose the endpoint set — all of them, at once.**
For each: method, path, permission, purpose, and the requirements it satisfies.

**Check consistency across the set before presenting:** same concept means same
field name, same filter semantics on list endpoints, same error code for the
same failure, identical resource shape in list and detail unless deliberately
different, uniform status codes and pagination.

**3. Stop for approval** of the set.

**4. Raise ambiguities as `Q-###`.**
This is where stopping is cheap. A requirement that does not say what happens on
failure, a field with no derivable meaning, an unstated transition legality — all
become questions, never assumptions.

An endpoint with a blocking question does not proceed to step 6.

**5. Derive story error codes.**
Every business rule that can be violated becomes an `ERR-###`. Append to
`plan/errors.md`.

**6. Write contracts** — one per endpoint, in `contracts/` mirroring the API
path. Every error case listed by `ERR-###`. Happy path only is not a contract.

**7. Write schemas** — request and response Pydantic models. They are the
contract made executable.

**8. Author tests (delegated).**
`test-author` writes the suite **from the contracts**, walking the edge-case
checklist and recording every category as covered or N/A.

**9. Write** `plan/endpoints/EP-###.md` for each, status `tests-written`.

**10. Run** `regen_indexes.py`, then `check_links.py`. Report.

---

## Output

| File | Contents |
|---|---|
| `contracts/<api-path>/<method>.md` | One per endpoint |
| `app/schemas/...` | Request and response models |
| `plan/endpoints/EP-###.md` | One per endpoint |
| `plan/errors.md` | Appended |
| `plan/questions.md` | Any new `Q-###` |
| `tests/...` | Red suite |

---

## Stop conditions

- Before approving the endpoint set
- Ambiguity that changes behaviour
- Two requirements implying different shapes for one resource
- A rule with no error code and no clear owner

---

## Do not

- Design endpoints one at a time
- Write a contract with only the happy path
- Implement anything — no models, DAL, services, or routers
- Invent a permission not in the matrix
- Resolve an ambiguity by assumption

---

## Next

`/build-endpoint <US-###>`
