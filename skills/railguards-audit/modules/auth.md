---
id: RG-AUTH
title: Authentication, sessions, and endpoint exposure
auditor: access
discovery: Always runs.
rules:
  RG-AUTH-001: Weak or reversible password storage
  RG-AUTH-002: Insecure session or token management
  RG-AUTH-003: Missing rate limiting or lockout on authentication
  RG-AUTH-004: User enumeration through authentication responses
  RG-AUTH-005: Privileged endpoint reachable without authentication
  RG-AUTH-006: Improper JWT or OAuth token validation
---

# Authentication, Sessions, and Endpoint Exposure

## R: Risk First
**Goal**: Ensure only the right identities reach protected functionality, and sessions cannot be stolen or forged.
**Risk**: Unauthorized access, credential theft, session hijacking, identity spoofing.
**Context**: Any application with users, sessions, API tokens, service credentials or administrative tools, including agent and MCP endpoints.

## A: Attached Constraints
- ALWAYS hash passwords with Argon2id, bcrypt, scrypt or PBKDF2; NEVER store plaintext or reversible encryption.
- ALWAYS enforce password policy server-side.
- ALWAYS use cryptographically random session identifiers and regenerate them after login.
- NEVER transmit credentials over unencrypted connections.
- ALWAYS implement logout that invalidates the server-side session.
- ALWAYS rate-limit or lock out repeated failed attempts.
- NEVER reveal whether a username exists through error messages or timing.
- ALWAYS validate token signature, algorithm, issuer, audience and expiry.
- NEVER expose privileged tools (admin, import/export, config, manual triggers) without authentication.

## I: Isolation
- **Trust boundaries**: anonymous vs authenticated, user vs admin, human vs service account, and agent or MCP clients acting on behalf of users.
- **Untrusted inputs**: credentials, tokens, cookies, `Authorization` headers, OAuth `state` and redirect parameters.
- **Least privilege**: scope tokens to the minimum audience and permissions; short-lived access tokens with rotation; separate admin authentication.

## L: Local Defaults

**When implementing login**:
- Hash with Argon2id or bcrypt; rate-limit by account and IP; issue a fresh session after success; set sensible timeouts.

**When implementing password reset**:
- Single-use, time-limited random tokens; email verification; invalidate existing sessions after change; log the event.

**When managing sessions**:
- Cookies with `Secure`, `HttpOnly`, `SameSite=Lax` or `Strict`; server-side invalidation on logout; regenerate IDs on privilege change; monitor concurrent sessions.

**When validating JWTs**:
- Pin the expected algorithm (reject `none` and algorithm confusion), verify `iss`, `aud`, `exp`, `nbf`; never trust unverified claims.

**When classifying endpoints** (decision tree):
1. Is the function mapped to a route or tool? If not, check whether every caller enforces authentication; flag it if it performs privileged operations and any caller does not.
2. If it is exposed, classify by functionality:
   - Public is acceptable: registration (`/register`, `/signup`), login (`/login`, `/auth`), password recovery (`/forgot-password`, `/reset`), marketing forms (`/contact`, `/newsletter`).
   - Authentication required: manual triggers (`/manual/*`, `/trigger/*`, `/admin/*`, `/tools/*`), data manipulation (`/import`, `/export`, `/sync`, `/migrate`), configuration (`/config`, `/settings`), and any MCP or agent tool that reads private data or changes state.
3. Priority of evidence: actual functionality, then call-chain analysis, then naming (weakest).

## G: Generative Path Checks
1. Are passwords hashed with an adaptive algorithm?
2. Are session tokens random, regenerated on login, and invalidated on logout?
3. Is authentication rate-limited with lockout or backoff?
4. Are error messages and timing uniform for unknown users?
5. Are credentials only sent over HTTPS?
6. Are JWT and OAuth tokens fully validated (algorithm, issuer, audience, expiry)?
7. Does every privileged route or tool enforce authentication, verified through its call chain?

## U: Uncertainty Disclosure
- **Safe default**: treat an endpoint as requiring authentication unless it clearly matches a public category.
- **Escalate when**: authentication is enforced by infrastructure you cannot see (API gateway, service mesh); report with `medium` confidence and name the assumption.

## A: Auditability
- **Log**: logins, failures, lockouts, password resets, privilege changes, token revocations, with user ID and source IP.
- **Never log**: passwords, session IDs, tokens, reset links.

## R: Review
1. Did a new route or tool appear without an authentication decorator or middleware?
2. Did token lifetimes or scopes grow?
3. Are service accounts and agent credentials still scoped to what they use?

**Core principle**: Classify endpoints by what they do, not what they are called. Hash credentials properly, keep sessions short-lived and unforgeable, validate every token claim, and require authentication for anything beyond basic registration and login.

## S: Spend
- Runs in: `railguards-auditor-access`.
- Gate: always.
- Scanners first: Semgrep rules for weak hashing, JWT misuse and insecure cookies.
- Read: route tables and middleware configuration first (one read), then only handlers lacking an auth guard.
- Skip: framework-provided auth internals.
