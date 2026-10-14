---
description: Add a requirement that affects nothing existing. Light path — no impact analysis.
argument-hint: <description of the new requirement>
---

# /new-requirement

For an addition that touches nothing already built. If anything existing is
affected, this is a **change request**, not a new requirement.

**Loads**
- `.claude/skills/requirement-decomposition.md`
- `.claude/skills/plan-file-format.md`
- `.claude/skills/error-registry.md`

**Calls:** `.claude/scripts/id_allocator.py`,
`.claude/scripts/regen_indexes.py`, `.claude/scripts/check_links.py`

---

## Input

`$ARGUMENTS` — the requirement, ideally in the requester's own words so it can
be stored verbatim.

If it arrived as a document rather than a sentence, extract the atomic
statements the same way decomposition does — one per entry.

---

## Steps

**1. Check it is actually new.**
Scan the inventory for overlap. If it contradicts, narrows, or redefines an
existing requirement, **stop** and say it belongs in `/change-request`.

This check is the whole reason this command is separate.

**2. Allocate `REQ-###`** and write the entry — verbatim text, source
(conversation, email, document), date, status active.

**3. Raise ambiguities as `Q-###`** rather than resolving them.

**4. Ask which phase** it belongs to. Do not assume the current one.

**5. New story or extend an existing one?**
Extending is right when it is the same capability and that story is not yet
complete. Otherwise create a story — a completed story stays completed.

**6. Derive error codes** for any violable rule it introduces.

**7. Run** `regen_indexes.py`, then `check_links.py`.

---

## Output

| File | Contents |
|---|---|
| `plan/requirements/inventory.md` | New `REQ-###` |
| `plan/stories/US-###.md` | New or updated |
| `plan/errors.md` | Any new codes |
| `plan/questions.md` | Any new `Q-###` |

---

## Stop conditions

- The requirement contradicts or modifies an existing one → `/change-request`
- Phase assignment unclear → ask
- It would extend a story already marked complete → that is a change request

---

## Do not

- Run impact analysis — there is nothing to trace
- Design endpoints — that is `/plan-story`
- Reopen a completed story
- Paraphrase the requirement
- Assume a phase

---

## Next

`/plan-story` when the story is ready to design.
