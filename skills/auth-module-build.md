# Skill: auth-module-build

**Tier:** invariant (two-token model, membership model, rotation, CSRF) ·
default (lifetimes, algorithms, transport)
**Read when:** building Phase 0, or changing anything under `app/auth/`.

**References**
- Reads: `.claude/docs/design-spec.md` §6, §7 ·
  `.claude/docs/decisions.md` TD-007…TD-014 ·
  `conventions.override.md` → section `auth-module-build`
- Related: `.claude/skills/auth-security-checklist.md` (**read both**),
  `.claude/skills/dal-conventions.md`,
  `.claude/skills/testing-strategy.md`
- Called by: `.claude/commands/build-endpoint.md`
- Reviewed by: `agents/security-reviewer.md` — **always, on every change here**

---

## Scope

**First-party auth with OIDC-shaped tokens.** Not an OpenID Provider.

Out of scope: client registration, consent screens, authorization code flow,
PKCE, discovery documents, third-party clients, SSO federation.

One issuer per platform; all tenants of that platform share it. Auth is
in-repo, instantiated per project.

---

## Why auth is built before any business endpoint

Tenant and roles come from the token context, and every DAL query filters on
tenant. Stubbing that means rewriting every endpoint and every test when real
auth lands. It is the most expensive retrofit in the project.

---

## The membership model *(invariant)*

**Identity is global. Authorization is per membership.** Three tables:

| Table | Notes |
|---|---|
| `users` | **No tenant column.** Email globally unique. Credentials here. |
| `memberships` | user × tenant, carrying **the roles held in that tenant**, plus status |
| everything else | tenant-scoped |

Roles live on the membership, never on the user. A user who is admin in one
tenant and viewer in another is the normal case, not an edge case.

---

## The two tokens *(invariant)*

| Token | Carries | May call |
|---|---|---|
| **Identity** | user, no tenant | list-my-tenants, exchange — nothing else |
| **Access** | user + one tenant + roles in that tenant | every business endpoint |

A **`typ` claim distinguishes them and is validated.** Middleware rejects an
identity token on a business route and an access token on the exchange route.

**Never** a single token listing all memberships with an active-tenant header —
tenant would then arrive from user input, defeating the isolation model.

Membership is **re-checked at exchange**, which is what makes short access
tokens sufficient for revocation.

---

## Build order

1. **Models + migration** — users, memberships, refresh tokens, signing keys
2. **Key generation and storage** — asymmetric, `kid` in the header
3. **Token issuance** — identity token at login; access token via exchange
4. **Validation middleware** — signature → `algorithms` → `aud` → `iss` →
   `typ` → expiry → tenant and role context
5. **RBAC matrix** from the requirements document, enforced in middleware
6. **Refresh rotation**, reuse detection, grace window
7. **Cookie + CSRF + CORS**
8. **Endpoints** — login, logout, token exchange, list-my-tenants
9. **Test token factory** — built alongside issuance; everything downstream
   depends on it
10. **Middleware test suite** — the deep one

Each step follows the normal inner loop: contract, tests first, bottom-up build.

---

## Tokens

**Access token lifetime: 15 minutes** *(default)*. This is the decision that
makes complicated revocation machinery unnecessary — a user removed from a
tenant is locked out within 15 minutes automatically, with no denylist and no
per-request lookup.

**Claims:** issuer, audience, subject, `typ`, issued-at, expiry, `kid` in the
header; plus tenant and roles on the access token.

Keep the claim set minimal. Every claim is a thing that can go stale.

---

## Refresh rotation *(invariant)*

- Each refresh issues a new token and invalidates the old
- **Reuse of a spent token means theft** → revoke the entire family
- Family revocation gives logout-everywhere and admin-force-logout for free

**Grace window — design it in, do not discover it.** Multiple tabs or a
retrying mobile client can fire two refreshes with the same token and trip
reuse detection, logging the user out for no reason. A short window where a
just-rotated token is still accepted prevents this; only genuine later reuse
triggers revocation.

---

## Transport *(default, cross-origin)*

| Token | Transport |
|---|---|
| Refresh | httpOnly cookie — `Secure`, `SameSite=None`, `Path` scoped to refresh/logout only, explicit `Max-Age` |
| Access | **response body**, held in frontend memory, sent as a bearer header |

**Because `SameSite=None` allows cross-site sending, CSRF validation on the
refresh endpoint is mandatory and part of Phase 0.** Not deferred.

**CORS with an explicit origin allowlist.** Never `*` with credentials.

**Never put the access token in a cookie as well** — mixing both makes every
endpoint CSRF-exposed rather than just the refresh endpoint.

---

## Passwords

argon2 *(default)*. Policy — minimum length, rejection of known-breached
passwords if available — recorded in the project config.

Never log, never return, never include in an error message.

---

## RBAC

The permission matrix (role × permission) is a committed config artifact derived
from the requirements document during `/ingest-requirements`.

Middleware enforces route-level permission. Record-level authorization —
whether this caller may act on this particular record in this state — is a
service concern.

**The matrix generates the middleware's permission tests**, so adding a role
automatically expands coverage.

---

## Test token factory

Built with issuance, not after. A fixture that mints a real signed token for any
tenant and role combination, in one line.

**Never a config flag that disables auth in test mode.** It makes tests easy and
eventually ships to production. The factory gives the same convenience while
exercising the real middleware on every request.

---

## Deferred, with seams designed

| Item | Seam that must exist now |
|---|---|
| JWKS endpoint | Keys stored with `kid`, public part retrievable |
| Key rotation | `kid` in header; validation selects key by `kid` |
| MFA | Login flow is a sequence, not a single step |
| Password reset | Token table generalised enough to carry one-time tokens |

---

## Common violations

| Symptom | Fix |
|---|---|
| Roles stored on the user record | Move to membership |
| One token with all memberships | Two tokens, tenant inside the signed access token |
| Tenant from an active-tenant header | Exchange for a tenant-scoped token |
| `typ` not validated | Validate; reject wrong type per route class |
| Refresh token in the response body | httpOnly cookie |
| Access token in a cookie | Response body, bearer header |
| CSRF deferred "until later" | It is Phase 0 under cross-origin |
| CORS `*` with credentials | Explicit allowlist |
| Auth disabled in tests | Token factory |
| Membership not re-checked at exchange | Re-check — this is what short tokens rely on |

---

## Overrides

Check `conventions.override.md` → section `auth-module-build` for lifetimes,
hashing choice, and transport.

Two-token model, membership model, rotation with reuse detection, and CSRF under
cross-origin are **invariant**.

**Read `.claude/skills/auth-security-checklist.md` alongside this file. It is
short and non-negotiable.**
