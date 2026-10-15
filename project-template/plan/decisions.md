# Project Decisions

Decisions made during this project, with reasoning.

**Scope:** project-level, IDs prefixed `DEC-`. Toolkit-level decisions use
`TD-###` and live in `.claude/docs/decisions.md`.

---

## Why this file exists

In six months nobody remembers why `/v2` exists, why one table soft-deletes and
another does not, or why a rule was relaxed. Without the reasoning, the same
argument gets had again — usually with less information than the first time.

**A decision is amended, never silently rewritten.** Add a new entry
superseding the old one.

---

## What gets recorded

- Resolution of any `Q-###`
- Every **breaking** contract change, with version-or-coordinate and why
- Business logic placed outside the service layer
- A cross-tenant query, with its justification
- Deferring or removing a requirement
- What happens to endpoints built against a removed requirement
- Soft-delete response choice — 404 or 410
- Unique-after-delete choice, and any partial index it needs
- Page-size-over-maximum behaviour — reject or clamp
- A convention override, if it has consequences beyond style
- Anything a future reader would call arbitrary

---

## Entry format

```
### DEC-001
**Date:** YYYY-MM-DD
**Affects:** REQ-### | US-### | EP-### | <component>
**Resolves:** Q-### (if applicable)

**Decision:** <what was decided>

**Reasoning:** <why — the part that is actually useful later>

**Alternatives rejected:** <what else was considered, and what it would cost>

**Consequences:** <what this makes harder or impossible later>
```

The **alternatives rejected** field matters most. A decision with no stated
alternative reads later as the only option, which is almost never true.

---

## Decisions

*None yet.*

---

## Superseded

*Kept with a pointer to what replaced them.*

*None yet.*
