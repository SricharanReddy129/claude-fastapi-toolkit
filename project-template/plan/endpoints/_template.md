---
id: EP-000
type: endpoint
story: US-000
requirements: [REQ-000]
status: planned
method: GET
path: /api/v1/<resource>
contract: contracts/<resource>/get.md
permission: <permission-name>
tenant_scoped: true
idempotency_key: false
errors: []
decisions: []
questions: []
---

# EP-000 — GET /api/v1/&lt;resource&gt;

**Purpose:** <one line>

**Notes:** <state transitions, side effects, ordering guarantees>

## Changelog

<!-- One line per change request that touched this endpoint -->

<!--
status values:
  planned         designed, no contract yet
  contracted      contract written and approved
  tests-written   test suite exists and is red
  building        implementation in progress
  done            green, contract verified, no open questions
  needs-rebuild   set by /change-request — blocks story completion

tenant_scoped: true means every query filters on tenant AND a
cross-tenant 404 test is mandatory. Never N/A.

idempotency_key: true on POST and non-idempotent PATCH where the
project config requires one.

errors / decisions / questions: ERR-###, DEC-###, Q-### lists.
Empty list when none.
-->
