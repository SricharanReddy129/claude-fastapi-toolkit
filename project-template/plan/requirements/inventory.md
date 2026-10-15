# Requirement Inventory

Every atomic statement from the source document, with **verbatim text**.

**Source document:** <path or name> · **Ingested:** <date>

---

## Rules

- **IDs are permanent.** Never renumbered, never reused
- **Text is verbatim.** Paraphrasing destroys the ability to answer "where did
  this rule come from"
- **One statement per entry.** A sentence with three rules becomes three entries
- **Nothing is deleted.** Mark `deferred` or `removed` with a date and reason
- **Every active requirement** is claimed by a story or explicitly deferred —
  `check_links.py` enforces this
- A revised source document is **diffed against this file** and applied as
  change requests. Decomposition is never re-run

---

## Entry format

```
### REQ-001
**Status:** active | deferred | removed
**Category:** functional | business-rule | non-functional | technical | out-of-scope
**Source:** <section / page / line>

> <verbatim text from the source document>

**Notes:** <only if clarification is needed — never a substitute for the text>
**Questions:** Q-### (if ambiguous)
**Changelog:**
- YYYY-MM-DD — CR-### — <what changed and why>
```

---

## Functional

*None yet.*

---

## Business rules

*None yet.*

---

## Non-functional

*None yet.*

---

## Technical

*None yet.*

---

## Out of scope

*Explicit exclusions from the source document. These are requirements too, and
the most commonly lost.*

*None yet.*

---

## Deferred and removed

*Kept with date and reason. Deleting means the same argument gets relitigated in
three months with no record of how it was settled.*

*None yet.*
