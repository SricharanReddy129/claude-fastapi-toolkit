# Conventions Index

Every rule in this toolkit, by tier. Scan this to see what is overridable
without reading the full spec.

**Tiers** (defined in `docs/design-spec.md` §3):

| Tier | Meaning |
|---|---|
| **INVARIANT** | Never overridable. Violating one is a bug, not a preference. No config switch exists. |
| **DEFAULT** | Ships with a value. A project may override in `conventions.override.md` with a reason and a date. |
| **CHOICE** | No default. Derived from the requirements document during `/ingest-requirements`, confirmed by the user. |

**Enforcement** column: `hook` = blocked or checked automatically ·
`script` = checked by a script · `review` = checked by `security-reviewer` ·
`—` = convention only, no mechanical check.

---

## INVARIANT

Cannot be overridden. No exceptions, no flags.

### Security and tenancy

| Rule | Enforcement | Spec | Owner |
|---|---|---|---|
| Every query on a tenant-scoped table filters on tenant | `script` `dal_guard.py` | §6.2 | `dal-conventions` |
| `tenant_id` comes from validated token context only — never body, query, or header | `script` `dal_guard.py` | §6.2 | `dal-conventions` |
| No service method trusts a tenant value passed up from the API layer | `review` | §6.3 | `service-conventions` |
| Every query on a soft-deleted table filters deleted rows | `script` `dal_guard.py` | §8.2 | `dal-conventions` |
| `algorithms` passed explicitly on every token decode | `review` | §7.7 | `auth-security-checklist` |
| `aud` and `iss` passed and validated on every decode | `review` | §7.7 | `auth-security-checklist` |
| `typ` claim validated — identity token rejected on business routes | `review` | §7.3 | `auth-security-checklist` |
| Every claim read from the verified payload, never the unverified header | `review` | §7.7 | `auth-security-checklist` |
| No secrets in committed files (contracts, stories, decisions, plan) | `review` | §16.9 | `error-registry`, `plan-file-format` |
| Idempotency key captured before processing | `review` | §8.3 | `service-conventions` |

### Code structure

| Rule | Enforcement | Spec | Owner |
|---|---|---|---|
| Business logic lives in `services/` — not routers, not DAL | `review` | §5.1 | `layered-architecture` |
| Services accept an injected session; never create or commit one | `review` | §8.5 | `service-conventions` |
| No raw error strings — every raise references a registry entry | `review` | §9.3 | `error-registry` |
| Error codes deprecated, never reused | — | §9.3 | `error-registry` |
| No `os.getenv` outside `app/settings.py` | `script` `dal_guard.py` | §16.9 | `service-conventions` |
| No blocking call inside an async function without thread offload | `script` `dal_guard.py` | §5.3 | `dal-conventions` |

### Tooling

| Rule | Enforcement | Spec | Owner |
|---|---|---|---|
| Dependencies enter only via `poetry add` | `hook` `guard_pip` | §16.8 | — |
| Everything runs through `poetry run` | — | §16.8 | — |
| `poetry.lock` committed and regenerated on change | `hook` | §16.8 | — |
| Claude never reads `.env` or `.env.*` (except `.env.example`) | `hook` `guard_env` | §16.9 | — |
| Every settings key present in `.env.example` | `hook` | §16.9 | — |
| One typed settings class, loaded once | `script` `dal_guard.py` | §16.9 | `service-conventions` |

### Testing

| Rule | Enforcement | Spec | Owner |
|---|---|---|---|
| No test commits | `review` | §10.5 | `testing-strategy` |
| No `TRUNCATE`, `DROP`, or `drop_all` in `tests/` | `hook` `guard_test_db` | §10.5 | `testing-strategy` |
| Tests create their own data; assume nothing pre-exists | — | §10.5 | `testing-strategy` |
| Token factory, never an auth-bypass flag | `review` | §10.4 | `testing-strategy` |
| Cross-tenant 404 test on every tenant-scoped endpoint | — | §10.3 | `edge-case-checklist` |
| Claude fixes code, never tests, without asking | `hook` | §10.8 | `testing-strategy` |

### Migrations

| Rule | Enforcement | Spec | Owner |
|---|---|---|---|
| Applied migrations are never edited | `hook` `guard_test_db` | §11.2 | `alembic-migrations` |
| Autogenerate output always reviewed before applying | — | §11.2 | `alembic-migrations` |
| Every migration has a working downgrade | — | §11.2 | `alembic-migrations` |

### Plan files

| Rule | Enforcement | Spec | Owner |
|---|---|---|---|
| Links point upward only | `script` `check_links.py` | §12.2 | `plan-file-format` |
| Downward indexes generated, never hand-edited | `hook` `on_plan_edit` | §12.3 | `plan-file-format` |
| IDs permanent, globally unique, never reused | `script` `check_links.py` | §12.1 | `plan-file-format` |
| Status lives in exactly one place per thing | `script` `regen_indexes.py` | §12.4 | `plan-file-format` |
| Requirements marked deferred or removed, never deleted | — | §14.3 | `requirement-decomposition` |
| Decomposition never re-run on a revised document | — | §14.4 | `requirement-decomposition` |
| Every cross-reference is a repo-relative path | `script` `check_links.py` | §16.7 | all |

### Auth architecture

| Rule | Enforcement | Spec | Owner |
|---|---|---|---|
| Identity global, authorization per membership | — | §6.1 | `auth-module-build` |
| Roles on the membership, never on the user | — | §6.1 | `auth-module-build` |
| Two token types, `typ` validated | `review` | §7.3 | `auth-module-build` |
| Refresh rotation with reuse detection | `review` | §7.4 | `auth-module-build` |
| CSRF validation on the refresh endpoint | `review` | §7.6 | `auth-module-build` |
| CORS allowlist explicit — never `*` with credentials | `review` | §7.6 | `auth-module-build` |

---

## DEFAULT

Overridable. Record the override and its reason in `conventions.override.md`,
in the section named for the owning skill.

| Rule | Default value | Spec | Owner |
|---|---|---|---|
| Layer build order | model → DAL → service → router | §5.2 | `layered-architecture` |
| SQLAlchemy mode | async (app), sync (Alembic) | §5.3 | `dal-conventions` |
| Pagination | signed cursor, immutable sort column | §8.1 | `dal-conventions` |
| Cross-tenant response | 404 | §6.4 | `dal-conventions` |
| Soft-deleted record response | 404 *(or 410 — decide per project)* | §8.2 | `dal-conventions` |
| Access token lifetime | 15 minutes | §7.4 | `auth-module-build` |
| Signing keys | asymmetric with `kid` | §7.4 | `auth-module-build` |
| Password hashing | argon2 | §7.4 | `auth-module-build` |
| Refresh transport | httpOnly cookie, `Secure`, `SameSite=None`, path-scoped | §7.6 | `auth-module-build` |
| Access token transport | response body, bearer header | §7.6 | `auth-module-build` |
| JWT library | PyJWT | §7.4 | `auth-security-checklist` |
| Error response | single envelope with user code, message, correlation ID | §9.2 | `error-registry` |
| Error code derivation | at `/ingest-requirements` and `/plan-story` | §9.4 | `error-registry` |
| Test isolation | one DB, transaction rollback | §10.5 | `testing-strategy` |
| Test authoring | upfront from contract, by `test-author` | §10.6 | `testing-strategy` |
| Test matrix | service units + one integration per endpoint + contract assertions | §10.2 | `testing-strategy` |
| Test fix attempts | 2 | §10.8 | `testing-strategy` |
| Audit | middleware, platform-admin only | §8.4 | — |
| Endpoint planning | whole story as a set, built one at a time | §13.3 | `contract-authoring` |
| Contract location | `contracts/` mirroring API paths | §12.6 | `contract-authoring` |
| Build-time ambiguity | stop only on behaviour-changing gaps and contract contradictions | §15.1 | `contract-authoring` |
| Security review trigger | auth changes (always) + story end + manual | §16.4 | — |
| Toolkit promotion | straight to `main` | §2.2 | — |
| Toolkit updates | between stories only | §2.4 | — |
| Progress output | one line per event, prefixed with endpoint ID | §13.5 | — |

---

## CHOICE

No default. Proposed by Claude from the requirements document during
`/ingest-requirements`, confirmed by the user, recorded in the project config.

| Choice | Notes | Spec |
|---|---|---|
| Database engine | PostgreSQL or MySQL | §1 |
| Role names | From the requirements doc | §7.8 |
| Permission matrix | Role × permission; generates middleware tests | §10.3 |
| Tenant-scoped entities | Which tables carry `tenant_id` | §6.1 |
| Soft-delete scope | Which tables soft-delete | §8.2 |
| Unique-after-delete | Whether a unique value is re-usable; may need a partial unique index | §8.2 |
| Idempotency scope | Which operations require a key | §8.3 |
| Sub-folder organisation | By feature or by resource, within each layer | §4 |
| Phase boundaries | Grouping of requirements | §13.2 |

---

## How to override

In `conventions.override.md` at the project root, under a heading matching the
owning skill:

```markdown
## dal-conventions

- **Pagination: offset/limit instead of cursor.**
  Reason: admin-only lists, fixed small datasets, frontend already built
  against offset. Date: 2026-xx-xx.
```

Skills read **only their own section**, so this file stays cheap to consult as
overrides accumulate.

Attempting to override an INVARIANT is refused — there is no mechanism, by
design (`docs/decisions.md` TD-032).

---

## Feedback loop

If the same override appears in three projects, it should stop being an
override and become either a new default or an explicit project choice. Review
override files across projects periodically — it is the best available signal
for what the next toolkit version should contain.
