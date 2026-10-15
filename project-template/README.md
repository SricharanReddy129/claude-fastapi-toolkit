# <PROJECT NAME>

<One paragraph: what this service does and who uses it.>

Multi-tenant FastAPI service. Built with the
[claude-fastapi-toolkit](<toolkit-url>).

---

## Stack

Python <version> · FastAPI · Poetry · Pydantic · SQLAlchemy (async) · Alembic ·
pytest · PyJWT · <PostgreSQL | MySQL>

---

## Setup

```bash
poetry install
cp .env.example .env     # fill in real values
```

Create the database, then:

```bash
poetry run alembic upgrade head
```

**One database serves both development and tests.** Tests isolate by
transaction rollback — nothing they create is ever committed, so your data is
untouched. See `.claude/skills/testing-strategy.md`.

---

## Running

```bash
poetry run uvicorn app.main:app --reload
```

---

## Tests

```bash
poetry run pytest
```

Tests mint real signed tokens via the token factory fixture. There is no
auth-bypass flag, by design.

---

## Dependencies

```bash
poetry add <package>
poetry add --group dev <package>
```

**Never `pip install`** — it is blocked, and it would leave `pyproject.toml`
out of date. Commit `poetry.lock`.

---

## Migrations

```bash
poetry run alembic revision --autogenerate -m "<what changed>"
# review the generated file line by line before applying
poetry run alembic upgrade head
poetry run alembic downgrade -1 && poetry run alembic upgrade head   # test it
```

Autogenerate is a draft. It misses constraint and index changes and will write
destructive operations without comment.

---

## Layout

```
app/
├── api/        routers — thin
├── schemas/    Pydantic request/response models
├── services/   all business logic
├── dal/        queries only — tenant + soft-delete filters
├── models/     SQLAlchemy models
├── auth/       token issuance, validation, RBAC
├── errors/     registry, envelope, handlers
├── adapters/   third-party integrations
└── utils/
```

Dependencies point downward only.

---

## Planning

Project state lives in `plan/`, not in anyone's head.

| File | Contents |
|---|---|
| `plan/index.md` | Current phase and story |
| `plan/requirements/inventory.md` | All requirements, verbatim |
| `plan/project-config.md` | Roles, tenancy, project choices |
| `plan/errors.md` | Error code registry |
| `plan/questions.md` | Open questions |
| `plan/decisions.md` | Decisions and reasoning |
| `contracts/` | API contracts — the source of truth |

If code and contract disagree, that is a bug.

---

## Working with Claude

```
/status                      where things stand
/plan-story US-###           design a story's endpoints
/build-endpoint US-###       build them
/verify-story US-###         check and mark complete
/change-request REQ-###      a requirement changed
```

Full list in `.claude/README.md`.

---

## Conventions

`.claude/CLAUDE-base.md` for the rules, `conventions.override.md` for this
project's deviations, `.claude/docs/design-spec.md` for the reasoning.

---

## Environment

`.env` is gitignored and never read by Claude. `.env.example` is the committed
contract — every key present, placeholder values. A new setting means updating
`.env.example` first.
