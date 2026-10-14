# Claude FastAPI Toolkit

A per-project Claude Code configuration for building multi-tenant FastAPI
applications in a layered architecture, with a traceable
requirement → story → endpoint → contract → test pipeline.

Personal toolkit. Opinionated by design.

---

## Start here

- **`docs/design-spec.md`** — every architectural and process decision. The
  source of truth. If anything else contradicts it, the spec wins.
- **`docs/decisions.md`** — why each default is the default, and what was
  rejected. Read before changing anything that looks arbitrary.
- **`docs/conventions-index.md`** — which rules are invariant, which are
  overridable defaults, which are per-project choices.

---

## Stack

Python · FastAPI · Poetry · Pydantic · SQLAlchemy (async app, sync Alembic) ·
Alembic · pytest · PyJWT · PostgreSQL or MySQL

**Assumes:** multi-tenant, first-party self-issued auth, cursor pagination,
soft delete, idempotency keys, a central error registry.

**Does not cover:** deployment, Docker, SSO federation, OpenID Provider
conformance.

---

## Using it in a project

```bash
cd my-project
git clone <toolkit-url> .claude
```

Git creates `.claude/` and places the repo contents directly inside. Then copy
`project-template/` contents to the project root and add `.claude/.git` to the
project's `.gitignore`.

### Then

```
/ingest-requirements <path-to-doc>   # inventory, project config, global error codes
                                      # → build foundation
                                      # → build Phase 0 auth
/plan-phases
/plan-story PH-1
/build-endpoint US-001
/verify-story US-001
```

---

## What's inside

| Folder | Contents |
|---|---|
| `skills/` | 13 skills — conventions and procedures |
| `commands/` | 12 commands — stage entry points |
| `agents/` | 3 subagents — requirements-analyst, test-author, security-reviewer |
| `hooks/` | 7 hooks — invariant enforcement |
| `scripts/` | 6 scripts — deterministic logic |
| `project-template/` | Copied to the project root at init |
| `docs/` | Design spec, decisions, conventions index |

`CLAUDE-base.md` holds the conventions loaded every session.
`settings.json` holds permissions and hook wiring.

---

## Commands

### Planning
| | |
|---|---|
| `/ingest-requirements` | Source doc → numbered inventory + project config + global error codes |
| `/plan-phases` | Group requirements into phases |
| `/plan-story` | Story + its full endpoint set + contracts + story error codes |

### Building
| | |
|---|---|
| `/build-endpoint` | Takes a story, builds endpoints one at a time |
| `/verify-story` | Full check; marks the story complete |
| `/security-review` | On-demand security pass |

### Change
| | |
|---|---|
| `/new-requirement` | Addition — no impact analysis needed |
| `/change-request` | Changed requirement — traces impact, stops for approval |

### Status and toolkit
| | |
|---|---|
| `/status` | Project state |
| `/toolkit-status` | Toolkit sync state |
| `/update-toolkit` | Pull toolkit changes |
| `/promote-to-toolkit` | Push a change to the toolkit |

---

## Changing the toolkit

**Project-specific?** → `conventions.override.md` at the project root.
Committed to the project. Never travels.

**Universal?** → Edit the file inside `.claude/`, then `/promote-to-toolkit`
(commits and pushes to `main`). The project is immediately on that commit.

**Pulling someone else's improvement?** → `/update-toolkit` (git pull inside
`.claude/`), between stories only — never mid-story.

> An edit inside `.claude/` that is neither promoted nor moved to overrides is
> an undecided state. `/toolkit-status` surfaces it.

### Invariants cannot be overridden

Tenant filtering · soft-delete filtering · explicit `algorithms`/`aud`/`iss` ·
tenant never from user input · no raw error strings · no secrets in committed
files · injected sessions · `poetry add` only.

No config switch exists for these. See `docs/design-spec.md` §3.

---

## Conventions worth knowing before first use

- **`.env` is never read by Claude.** `.env.example` is the committed contract.
- **Dependencies via `poetry add` only.** `pip install` is blocked.
- **One database.** Tests isolate by transaction rollback — no test commits,
  truncates, or drops.
- **Tests are written from the contract before implementation**, by a subagent.
- **Claude fixes code, never tests, without asking.**
- **Plan files link upward only.** Downward indexes are generated, never
  hand-edited.
- **Every cross-reference is a repo-relative path**, never a bare name.

---

## Status

v1 — in construction. Build order is in `docs/design-spec.md` §18.
