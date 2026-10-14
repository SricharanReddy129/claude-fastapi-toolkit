---
description: Run a read-only security pass over a scope you name.
argument-hint: [US-### | path | auth | all]
---

# /security-review

On-demand pass. Runs automatically at `/verify-story` and on every change under
`app/auth/` — this command is for everything else.

**Delegates to:** `.claude/agents/security-reviewer.md` (read-only)
**Calls:** `.claude/scripts/dal_guard.py`

**Reference skills the reviewer operates under**
- `.claude/skills/auth-security-checklist.md`
- `.claude/skills/dal-conventions.md`
- `.claude/skills/service-conventions.md`
- `.claude/skills/router-conventions.md`

---

## Input

`$ARGUMENTS` — one of:

| Scope | Meaning |
|---|---|
| `US-###` | That story's diff |
| a path | That file or directory |
| `auth` | Everything under `app/auth/` |
| `all` | Whole codebase — slow, use sparingly |

Default when omitted: uncommitted changes.

---

## What is checked

**Auth** — decode without explicit `algorithms`; missing `aud` or `iss`; claims
read from an unverified header or decode; `verify=False` or any auth-disabling
branch; unknown-`kid` fallback; token or password in a log; error responses that
distinguish failure causes to the client; missing CSRF on refresh; CORS wildcard
with credentials; hardcoded key or secret.

**Tenancy** — DAL query on a scoped table without a tenant filter; missing
soft-delete filter, including on joined tables; tenant read from request input;
service trusting a tenant value from the API layer; cross-tenant query not
explicitly named as such.

**Code** — raw error strings; `HTTPException` in a service; `os.getenv` outside
settings; service creating or committing a session; blocking call inside an
async function; secret in a committed file.

---

## Output

Findings grouped by severity, each with file, line, what rule it breaks, and
which skill states that rule.

| Severity | Meaning |
|---|---|
| **Critical** | Auth bypass, cross-tenant leak, exposed secret |
| **High** | Missing mandatory filter, unvalidated claim |
| **Medium** | Convention violations with security implications |
| **Low** | Hygiene |

A clean pass says so plainly and names the scope checked.

---

## Do not

- Fix anything. This is **read-only** — report, do not repair
- Suppress a finding because it looks intentional; report it and let the user
  decide
- Mark a story verified from here; that is `/verify-story`
- Skip `auth` scope when auth files changed

---

## Note

Per-endpoint review is deliberately **not** automatic — most endpoints are
plumbing, and reviewing each one burns tokens confirming nothing changed. The
accepted tradeoff is that a bad pattern can repeat across a few endpoints before
story-end review catches it. Auth code, where a silent bug is worst, is covered
on every change.

Reasoning: `.claude/docs/decisions.md` TD-028.
