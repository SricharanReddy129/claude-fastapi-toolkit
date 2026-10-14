# Skill: auth-security-checklist

**Tier:** invariant — all of it
**Read when:** writing, changing, or reviewing anything that issues, validates,
or reads a token. Short by design. No overrides exist.

**References**
- Reads: `.claude/docs/design-spec.md` §7.7
- Related: `.claude/skills/auth-module-build.md`
- Used by: `agents/security-reviewer.md`

---

## Why this file is separate

Writing your own token issuer is the highest-risk work in the project — not
because the happy path is hard, but because **the failure modes are silent**.
A token that validates when it shouldn't looks exactly like a token that
validates correctly. Nothing breaks, no test fails, and you find out from
someone else.

These checks are the difference. Treat a violation as a defect, not a
suggestion.

---

## The four PyJWT traps

PyJWT is deliberately unopinionated. These are on you.

**1. Pass `algorithms` explicitly on every decode.**
The single most important line in the auth code. Omitting it is how `alg: none`
and HS/RS confusion attacks land. Accept exactly one algorithm. **Never read
`alg` from the token header to decide how to verify it** — the attacker controls
that header.

**2. Pass `aud` and `iss` on every decode.**
PyJWT validates expiry by default. It does **not** validate audience or issuer
unless you ask. A token minted for another service or another platform will
otherwise verify cleanly.

**3. JWKS is not automatic.**
Key generation, storage, rotation, and `kid` handling are your code. Validation
selects the key by `kid`; a token with an unknown `kid` is rejected, never
fallback-verified against a default key.

**4. Read every claim from the verified payload.**
Never from the unverified header. Never from a second decode-without-verify
call. If a value influences any decision, it must come from the payload that
signature verification returned.

---

## Validation order

Every request, no shortcuts, no caching of the result across requests:

1. Token present and well-formed
2. `kid` resolves to a known key
3. Signature verifies with the pinned algorithm
4. `iss` matches
5. `aud` matches
6. `typ` matches what this route class accepts
7. Expiry and not-before, with bounded clock skew
8. Only then: extract subject, tenant, roles

A failure at any step is a rejection. Never a partial pass, never a downgrade
to a weaker check.

---

## Hard rules

- **No `verify=False`**, no disabled signature verification, no "just for
  testing" branch. Tests use the token factory with real signed tokens.
- **No auth bypass flag.** Not behind a setting, not behind a debug check.
- **No secret or private key in code, in a committed file, or in a log.**
- **Tenant never from user input.** Body, query, header — all untrusted.
- **Unbounded clock skew is not acceptable.** Bound it tightly.
- **Unknown or missing `kid` → reject.** No default-key fallback.
- **Error responses must not leak which check failed.** "Invalid token" to the
  client; the specific failure goes to logs with the correlation ID.
- **Never log a token**, whole or partial.
- **Passwords never logged, returned, or included in an error message.**

---

## Refresh-specific

- Rotation on every refresh; the old token is invalidated
- Reuse of a spent token revokes the entire family
- A grace window exists for concurrent refreshes, and it is **short** and
  explicit — not an open-ended tolerance
- Refresh cookie is `HttpOnly`, `Secure`, `SameSite=None`, path-scoped
- **CSRF validation on the refresh endpoint** — mandatory under cross-origin
- Logout invalidates the family, not just the presented token

---

## Review triggers

`security-reviewer` runs **on every change under `app/auth/`** — no exceptions,
no batching to story end. Elsewhere it runs at `/verify-story`.

Rationale: a bad pattern in ordinary CRUD is a bug you fix. A bad pattern here
is an unlocked door nobody notices.

---

## What the reviewer flags

- Decode without explicit `algorithms`
- Decode without `aud` or `iss`
- Any claim read from the header or an unverified decode
- `verify=False` or equivalent
- Any auth-disabling flag or branch
- Tenant sourced from request input
- Token or password in a log statement
- Unknown-`kid` fallback
- Error responses that distinguish failure causes to the client
- Missing CSRF check on refresh
- CORS allowing credentials with a wildcard origin
- Hardcoded key or secret

---

## No overrides

Nothing in this file is overridable. There is no section for it in
`conventions.override.md`, by design.
