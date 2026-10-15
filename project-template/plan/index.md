# Project Plan — <PROJECT NAME>

**Read this first. Keep it short — it is read on every command.**
Detail lives in the leaf files. Anything long here is in the wrong place.

---

## Position

| | |
|---|---|
| **Current phase** | — |
| **Current story** | — |
| **Last verified story** | — |

---

## Phases

| ID | Goal | Status |
|---|---|---|
| PH-0 | Authentication foundation | not started |

*Status is derived from stories by `.claude/scripts/regen_indexes.py`.
Do not hand-edit.*

---

## Counts

| | |
|---|---|
| Requirements | 0 active · 0 deferred · 0 removed |
| Stories | 0 complete / 0 |
| Endpoints | 0 done · 0 building · 0 planned · 0 needs-rebuild |
| Open questions | 0 |
| Error codes | 0 |

---

## Needs attention

*Endpoints marked `needs-rebuild`, stories reopened by a change request,
blocking questions. Empty is the normal state.*

—

---

## Where things are

| | |
|---|---|
| Requirements | `plan/requirements/inventory.md` |
| Project config | `plan/project-config.md` |
| Phases | `plan/phases/PH-#.md` |
| Stories | `plan/stories/US-###.md` |
| Endpoints | `plan/endpoints/EP-###.md` |
| Changes | `plan/changes/CR-###.md` |
| Decisions | `plan/decisions.md` |
| Questions | `plan/questions.md` |
| Errors | `plan/errors.md` |
| Generated views | `plan/generated/` — never hand-edit |
| Contracts | `contracts/` |

---

## Build order

1. Repo skeleton and tooling
2. `/ingest-requirements`
3. Foundation — settings, DB, base model, Alembic, error registry, test harness
4. Phase 0 — auth
5. `/plan-phases`
6. Per story: `/plan-story` → `/build-endpoint` → `/verify-story`
