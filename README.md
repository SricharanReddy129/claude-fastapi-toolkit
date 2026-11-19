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

# Starting a new project

Six steps. Do them in order.

## 1. Create the folder and clone the toolkit

```bash
mkdir my-erp
cd my-erp
git clone <toolkit-url> .claude
```

**Git creates `.claude/` — do not create it yourself.** The `.claude` at the
end of that command is the destination name; the repo contents land directly
inside it.

## 2. Run the init script

```bash
python .claude/scripts/init_project.py --name "My ERP"
```

This copies `project-template/` into the project root, renames
`gitignore.template` to `.gitignore`, and substitutes the project name.

**Do not copy anything by hand.** The script refuses to run if any target file
already exists, so a stray hand-made `.gitignore` will block the whole thing.

Check it with `--dry-run` first if you want to see what it will create.

## 3. Start the project's git repo

```bash
git init
git add -A
git commit -m "Initial skeleton from toolkit"
```

`.gitignore` already excludes `.claude/.git/`, so the toolkit's repo and the
project's repo stay out of each other's way.

## 4. Set up Python

```bash
poetry init
poetry install
cp .env.example .env
```

Then fill in real values in `.env`. **Claude never reads or writes `.env`** —
that is a hook-enforced invariant. When a new setting is needed, Claude edits
`.env.example` and tells you what to add.

## 5. Create the database

One database serves both development and tests. Tests isolate by transaction
rollback, so nothing they create is ever committed.

Put the connection string in `.env`.

## 6. Open Claude Code and run `/init-project`

```
/init-project
```

It confirms what landed, asks for a one-line description of the service, and
writes it into `CLAUDE.md`.

---

# The development flow

## Once per project

```
/ingest-requirements path/to/requirements-doc.md
```

Produces the numbered requirement inventory, the project config proposal
(roles, tenancy, idempotency scope — all derived from the document and
confirmed by you), and the global error codes.

**Then resolve any blocking questions it raises.** Ambiguity is cheapest to fix
here.

**Then build the foundation** — settings, DB engine, base model, Alembic, error
registry, test harness. Ask Claude to do it; there is no command, because it is
one-off work shaped by the project config.

**Then build Phase 0 auth.** It goes through the normal story flow below, but
it comes first — every endpoint after it depends on tenant and role context.

```
/plan-phases
```

Groups requirements into phases and stories.

## Per story, repeating

```
/plan-story US-001
```

Designs **all** the story's endpoints as a set, writes contracts and schemas,
derives story error codes, and has `test-author` write the test suite from the
contracts. The suite will be red — that is correct.

```
/build-endpoint US-001
```

Works through the endpoints one at a time: model → migration → DAL → service →
router, running tests at each layer. Halts on a failure or an ambiguity.

```
/verify-story US-001
```

Full check — tests, contract drift, edge-case coverage, security review, open
questions. Marks the story complete if everything passes.

Then `/plan-story` on the next one.

## When requirements change

```
/new-requirement "..."       # addition, nothing existing affected
/change-request REQ-014      # something changed — traces impact, stops for approval
```

## Checking in

```
/status            # phase, story, endpoints, blockers
/toolkit-status    # toolkit sync state, active overrides
```

---

## What's inside

| Folder | Contents |
|---|---|
| `skills/` | 13 skills — conventions and procedures |
| `commands/` | 14 commands — stage entry points |
| `agents/` | 3 subagents — requirements-analyst, test-author, security-reviewer |
| `hooks/` | 7 hooks plus `_hook.py`, the shared protocol helper |
| `scripts/` | 8 scripts, including `_plan.py`, the shared plan parser |
| `project-template/` | Copied to the project root by `init_project.py` |
| `docs/` | Design spec, decisions, conventions index |

`CLAUDE-base.md` holds the conventions loaded every session.
`settings.json` holds permissions and hook wiring.

---

## Commands

### Setup
| | |
|---|---|
| `/init-project` | Finish setup after `init_project.py` has run |

### Planning
| | |
|---|---|
| `/ingest-requirements` | Source doc → inventory + project config + global error codes |
| `/plan-phases` | Group requirements into phases and stories |
| `/plan-story` | Story's full endpoint set + contracts + error codes + tests |

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
| `/add-error-code` | Mid-build discovery. The exception, not the path |

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

**Pulling an improvement made elsewhere?** → `/update-toolkit` (git pull inside
`.claude/`), between stories only — never mid-story.

> An edit inside `.claude/` that is neither promoted nor moved to overrides is
> an undecided state. `/toolkit-status` surfaces it.

### Invariants cannot be overridden

Tenant filtering · soft-delete filtering · explicit `algorithms`/`aud`/`iss` ·
tenant never from user input · no raw error strings · no secrets in committed
files · injected sessions · `poetry add` only · upward-only plan links.

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

v1. Hook event shape and `settings.json` schema should be verified against the
current Claude Code docs — those are the parts most likely to have moved.
`contract_diff.py` and `dal_guard.py` have not yet run against a real
application and will need tuning.

Build order for the toolkit itself is in `docs/design-spec.md` §18.
