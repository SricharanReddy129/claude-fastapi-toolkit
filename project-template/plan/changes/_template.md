---
id: CR-000
type: change-request
date: YYYY-MM-DD
requirement: REQ-000
status: proposed
classification: additive
stories: []
endpoints: []
contracts: []
decisions: []
---

# CR-000 — <short title>

## What changed

<The new requirement text, verbatim where possible, or the nature of the change.>

## Impact

| Affected | IDs / paths | Status at time of change |
|---|---|---|
| Stories | US-### | |
| Endpoints | EP-### | |
| Contracts | contracts/... | |
| Tests | tests/... | |
| Error codes | ERR-### added / deprecated | |

## Classification

| Contract | What changed | Class |
|---|---|---|
| contracts/... | | additive / **breaking** |

<!--
When unsure, classify as breaking. Being wrong that way costs a
conversation; the other way breaks a frontend.
-->

## Decision

**Approved:** <who> on YYYY-MM-DD

**For breaking changes:** version the endpoint | coordinate with the consumer

**Reasoning:** <why — logged separately as DEC-###>

## Applied

- [ ] Requirement changelog updated
- [ ] Contracts updated
- [ ] Error codes added / deprecated
- [ ] Schemas updated
- [ ] Tests regenerated
- [ ] Endpoints marked needs-rebuild
- [ ] Story marked incomplete
- [ ] DEC-### logged

<!--
status: proposed | approved | applied
classification: additive | breaking  (breaking if ANY contract change is)
stories / endpoints / contracts / decisions: what this CR touched.
Filled in as the change is applied.
-->
