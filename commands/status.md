---
description: Where the project stands — phase, story, endpoints, open questions, blockers.
argument-hint: (none)
---

# /status

Project state. Short enough to run constantly.

For toolkit sync state, use `/toolkit-status` — deliberately separate so this
one stays scannable.

**Calls:** `.claude/scripts/regen_indexes.py`,
`.claude/scripts/check_links.py`

---

## Steps

**1. Regenerate** indexes so status is real, not stale.

**2. Read** `plan/index.md` and the generated views. **Not** individual endpoint
files unless something needs explaining.

**3. Report**, in this order:

| Section | Contents |
|---|---|
| **Position** | Current phase, current story |
| **Phase progress** | Stories complete / total |
| **Story progress** | Endpoints by status — done, building, tests-written, planned, **needs-rebuild** |
| **Blockers** | Open `Q-###` with what each blocks |
| **Needs attention** | Endpoints marked `needs-rebuild`, stories reopened by a change request |
| **Integrity** | `check_links.py` result — only if it fails |

**4. Suggest the next action** — one line. Usually `/plan-story`,
`/build-endpoint`, or `/verify-story`.

---

## Rules

- **Derived status only.** Story and phase status come from endpoints. Never
  hand-maintained, never inferred from conversation
- `needs-rebuild` is always surfaced — it is the state that silently rots a plan
- If `check_links.py` passes, say nothing about it
- Keep it to a screen. Detail lives in the leaf files

---

## Do not

- Load the source document
- Read every endpoint file to assemble a summary
- Fix anything found along the way — report it
- Include toolkit sync state
