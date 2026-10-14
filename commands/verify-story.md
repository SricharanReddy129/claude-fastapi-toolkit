---
description: Run the full check on a story and mark it complete if everything passes.
argument-hint: <US-###>
---

# /verify-story

The gate. A story is complete only when this passes.

**Loads**
- `.claude/skills/testing-strategy.md`
- `.claude/skills/edge-case-checklist.md`

**Delegates to:** `.claude/agents/security-reviewer.md`
**Calls:** `.claude/scripts/contract_diff.py`,
`.claude/scripts/dal_guard.py`, `.claude/scripts/check_links.py`,
`.claude/scripts/regen_indexes.py`

---

## Input

`$ARGUMENTS` — a `US-###`. If omitted, use the story whose endpoints are all
marked done.

---

## Checks

Run all of them, then report **everything** that failed — not just the first.

**1. Endpoint completeness.** Every endpoint in the story is `done`. Nothing is
`needs-rebuild`.

**2. Full test suite.** Not just this story's tests — a story can break another.

**3. Contract drift.** `contract_diff.py` across the story's endpoints. Live
OpenAPI must match committed contracts exactly.

**4. Edge-case record.** Every endpoint's test file records every category as
covered or N/A with a reason. A missing or partial record **fails** — the story
is not done.

**5. Cross-tenant tests present.** Every endpoint touching tenant data has one.
Mandatory, never N/A.

**6. Role-binding tests present.** One allowed role passes, one disallowed gets
403.

**7. DAL guard.** `dal_guard.py` over the story's diff — tenant filters,
soft-delete filters, tenant from input, `os.getenv`, blocking calls in async.

**8. Security review (delegated).** `security-reviewer` over the **whole story
diff**, read-only.

**9. Open questions.** No unresolved `Q-###` attached to any endpoint in the
story.

**10. Link integrity.** `check_links.py`.

---

## On pass

Mark the story complete. Run `regen_indexes.py` — phase status rolls up
automatically.

Report: endpoints completed, tests run, security review summary.

---

## On failure

**Do not mark complete.** Do not fix anything automatically beyond mechanical
test failures.

Report each failure with what it is and which endpoint it belongs to. Let the
user decide what to address first.

---

## Do not

- Mark complete with any check failing
- Skip the full suite to save time
- Treat a missing edge-case record as a formality
- Mark N/A on a cross-tenant test
- Resolve a security finding silently — report it
- Hand-edit story or phase status; it is derived

---

## Next

`/plan-story` on the next story, or `/status` to see where the phase stands.
