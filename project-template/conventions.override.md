# Convention Overrides

Project-specific deviations from the toolkit defaults.

**This file supersedes `.claude/skills/*.md`. It cannot override invariants.**

---

## How to use this

Each section is named for the skill it overrides. Skills read **only their own
section**, so this file stays cheap to consult as overrides accumulate.

Every override carries a **reason** and a **date**. An override with no reason
is indistinguishable from an accident six months later.

**Format:**

```
## <skill-name>

- **<What is different>.**
  Reason: <why this project needs it>. Date: YYYY-MM-DD.
```

---

## What belongs here

| Belongs here | Does not |
|---|---|
| A default done differently in this project | A universal improvement → `/promote-to-toolkit` |
| A project-specific rule the toolkit has no opinion on | A project fact → `CLAUDE.md` |
| | Project state or decisions → `plan/decisions.md` |
| | An attempt to weaken an invariant — refused by design |

If an override would mean an error, risk, or disagreement goes unraised, it does
not belong in any file.

---

## Invariants cannot be overridden

Tenant filtering · soft-delete filtering · explicit `algorithms`/`aud`/`iss` ·
tenant never from user input · no raw error strings · no secrets in committed
files · injected sessions · `poetry add` only · upward-only plan links.

There is no mechanism, by design. See `.claude/docs/decisions.md` TD-032.

---

## Sections

Add a section only when this project actually overrides something. Empty
sections are noise.

<!--
## layered-architecture
## dal-conventions
## service-conventions
## router-conventions
## auth-module-build
## testing-strategy
## edge-case-checklist
## error-registry
## alembic-migrations
## requirement-decomposition
## contract-authoring
-->

<!-- auth-security-checklist and plan-file-format have no override sections,
     deliberately. -->

---

## Review

If the same override appears across three projects, it should stop being an
override and become a toolkit default or an explicit project choice.

`/toolkit-status` lists what is active here.
