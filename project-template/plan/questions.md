# Open Questions

Ambiguities raised rather than resolved by assumption.

**A question written only in a conversation does not survive context
compaction.** That is why this file exists.

---

## Rules

- Raised during decomposition, contract authoring, or a build stop
- **Never resolved by a reasonable assumption** — that is the whole point
- A **blocking** question stops the work it blocks. No proceeding "for now"
- Resolution points at a `DEC-###`; the question is not deleted
- `/verify-story` fails if any endpoint in the story has an unresolved question

---

## Entry format

```
### Q-001
**Status:** open | resolved
**Raised:** YYYY-MM-DD, during <command or stage>
**Blocks:** REQ-### | US-### | EP-### | nothing
**Severity:** blocking | non-blocking

**Question:** <what is unclear>
**Context:** <the text or situation that raised it>
**What would resolve it:** <the specific answer needed>

**Resolution:** DEC-### — <one line> (YYYY-MM-DD)
```

---

## What to raise

| Signal | Example |
|---|---|
| Unquantified term | "fast", "secure", "large", "soon" |
| Undefined role or entity | A role named once, never described |
| No stated failure behaviour | What happens when the rule is violated? |
| Contradiction | Two sections implying different shapes |
| Implied but undescribed feature | Referenced in passing, never specified |
| Underivable field meaning | Format, units, or semantics unstated |
| Unstated transition legality | Can this move to that state? |
| Rule with no error code | A violable rule nobody named |

---

## Open

*None yet.*

---

## Resolved

*Kept, not deleted — the reasoning is often needed again.*

*None yet.*
