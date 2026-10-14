---
description: Add an error code discovered mid-build. The exception path — codes are normally derived during planning.
argument-hint: <description of the failure case>
---

# /add-error-code

**This is the exception, not the normal path.**

Codes are derived at `/ingest-requirements` (global) and `/plan-story`
(story-specific), so they exist before the code that raises them.

Needing this command usually means a business rule was missed during planning.
That is worth noticing, not just patching.

**Loads**
- `.claude/skills/error-registry.md`

**Calls:** `.claude/scripts/id_allocator.py`,
`.claude/scripts/check_links.py`

---

## Steps

**1. Check it does not already exist.**
Scan `plan/errors.md`. A near-match usually means the existing code should be
used, or that two failures should share a user code.

**2. Ask where it came from.**

| Origin | Action |
|---|---|
| A requirement that was never decomposed into a rule | Note the planning gap; the requirement may need a `/change-request` |
| A rule discovered while building | Note it; the contract probably needs updating too |
| A technical failure with no business meaning | Fine — these legitimately surface late |

**3. Allocate `ERR-###`** and write the entry: technical code, user code, HTTP
status, user message, developer message, category, originating `REQ-###` or
`US-###`.

**4. Check user-code granularity.**
Technical codes are specific — one per distinct failure. User codes are coarse
— if two failures lead to the same user action, they share a user code. Do not
mint a new user code reflexively.

**5. Update the contract** if the endpoint's contract does not list this failure.
A contract that omits an error case is incomplete.

**6. Run** `check_links.py`.

---

## Stop conditions

- A near-identical code exists → use it
- The case implies a requirement that was never captured → raise it
- The endpoint's contract would need a **breaking** change → that is
  `/change-request`, not this command

---

## Do not

- Reuse a deprecated code
- Delete a code — deprecate with a pointer to its replacement
- Add a code without an originating requirement or story
- Put technical detail in a user message
- Skip updating the contract

---

## Note

If this command is being used often, planning is not catching violable business
rules. Worth reviewing how `/plan-story` is deriving codes rather than treating
each instance as a one-off.
