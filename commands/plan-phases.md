---
description: Group requirements into phases and stories. Also used to re-plan phase boundaries later.
argument-hint: (none)
---

# /plan-phases

Pass two of decomposition. Groups existing `REQ-###` entries into phases, then
into stories.

**Loads**
- `.claude/skills/requirement-decomposition.md`
- `.claude/skills/plan-file-format.md`

**Calls:** `.claude/scripts/id_allocator.py`,
`.claude/scripts/regen_indexes.py`, `.claude/scripts/check_links.py`

---

## Preconditions

- `plan/requirements/inventory.md` exists
- No blocking `Q-###` that would change scope

If blocking questions remain, list them and stop.

---

## Steps

**1. Read** the inventory and `plan/project-config.md`. Not the source document.

**2. Propose phases.**
Phase 0 is always auth. Each phase delivers something coherent and
demonstrable. Dependencies point backward only. Prefer fewer, larger phases —
these are planning units, not sprints.

**3. Propose stories per phase.**
One feature or capability each, sized so its endpoints can be designed as a
consistent set. More than roughly six endpoints usually means two stories. One
endpoint is fine. Cross-cutting concerns are conventions, not stories.

**Endpoints are not decided here.** That is `/plan-story`.

**4. Check coverage.**
Every active requirement lands in a story or is explicitly deferred or
out-of-scope. Report anything unclaimed **before** asking for approval.

**5. Stop for approval.** Present phases, stories, requirement coverage, and
anything unclaimed.

**6. Write** `plan/phases/PH-#.md` and `plan/stories/US-###.md` with upward
links only.

**7. Run** `regen_indexes.py`, then `check_links.py`. Report.

---

## Re-planning

Running this again regroups **existing** stories when phase boundaries no longer
make sense.

It never touches requirement IDs, contracts, or endpoint status. Stories already
complete stay complete.

Record the reason in `plan/decisions.md`.

---

## Output

| File | Contents |
|---|---|
| `plan/phases/PH-#.md` | Goal, entry and exit criteria, status |
| `plan/stories/US-###.md` | Parent phase, requirement IDs, goal, status |
| `plan/generated/` | Regenerated |
| `plan/index.md` | Updated with the phase list |

---

## Stop conditions

- Blocking questions unresolved
- A requirement neither claimed nor explicitly deferred
- Before writing — always an approval point

---

## Do not

- Design endpoints
- Create new requirements — that is `/new-requirement`
- Renumber anything
- Hand-write story → endpoint lists; those are generated

---

## Next

Build foundation, then Phase 0 auth, then `/plan-story` on the first story.
