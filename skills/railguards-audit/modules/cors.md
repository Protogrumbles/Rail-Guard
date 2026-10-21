---
id: RG-CORS
title: CORS misconfiguration
auditor: web
discovery: CORS headers, middleware, or configuration exist.
rules:
  RG-CORS-001: Overly permissive or reflected CORS origin
---

# CORS Misconfiguration

## R: Risk First
**Goal**: Assess CORS misconfigurations by real exploitability.
**Risk**: Over-classifying CORS wastes remediation effort; under-classifying credentialed wildcard origins exposes data cross-origin.
**Context**: Only applications that already implement CORS.

## A: Attached Constraints
- ONLY assess CORS when an implementation exists.
- NEVER recommend adding CORS where none exists.
- ALWAYS default to LOW for standard misconfigurations.
- NEVER assign HIGH or CRITICAL without confirmed exploitability.

## I: Isolation
- **Trust boundaries**: the browser same-origin policy between the app's origin and other origins.
- **Untrusted inputs**: the `Origin` request header (attacker-controlled when reflected).
- **Least privilege**: allow only the exact origins that need access; avoid `Access-Control-Allow-Credentials: true` unless required.

## L: Local Defaults

**Discovery patterns**:
- Headers: `Access-Control-Allow-Origin`, `-Methods`, `-Headers`, `-Credentials`.
- Node.js: `cors()`, `app.use(cors`, `require('cors')`, `res.header('Access-Control`.
- Python: `flask_cors`, `CORS(app)`, `@cross_origin`, `django-cors-headers`, `CorsMiddleware`.
- Java/Spring: `@CrossOrigin`, `CorsConfiguration`, `CorsRegistry`, `CorsFilter`, `allowedOrigins`.
- .NET: `UseCors`, `EnableCors`, `WithOrigins`, `AllowAnyOrigin`, `AllowCredentials`.
- PHP: `header('Access-Control-Allow-Origin`. Ruby: `rack-cors`, `origins '*'`. Go: `cors.New`, `cors.Default`, `AllowedOrigins`, `rs/cors`.
- Config files: `cors: enabled: true`, `<cors>`, `<cors-configuration>`.

**Quick assessment**:
1. CORS implemented? No → skip.
2. Misconfigured (wildcard with credentials, reflected `Origin`, `null` allowed, suffix/prefix matching)? No → no finding.
3. Exploitability:
   - Returns sensitive data to credentialed cross-origin requests → MEDIUM or higher.
   - Combined with XSS or CSRF weaknesses → HIGH or higher.
   - Critical business system → consider MEDIUM.
   - Otherwise → LOW (default).

**MEDIUM requires all of**: attacker-controlled origins allowed with credentials, state-changing or sensitive endpoints with weak CSRF protection, and one secondary weakness (XSS, CSRF bypass, sensitive data in responses).

**Secure configuration**: an explicit origin allowlist compared by exact match; credentials only when needed; methods and headers limited to what the client uses.

## G: Generative Path Checks
1. Does the application send CORS headers?
2. Is the allowed origin a wildcard or reflected while credentials are allowed?
3. Do affected endpoints return sensitive data?
4. Are there state-changing endpoints with weak CSRF protection?
5. Are secondary weaknesses (XSS, CSRF) present?

## U: Uncertainty Disclosure
- **Safe default**: LOW with a note on what would raise it.
- **Escalate when**: credentialed reflection is confirmed on endpoints returning personal or financial data.

## A: Auditability
- **Log**: rejected cross-origin requests on sensitive endpoints, if the framework supports it.

## R: Review
1. Did the origin allowlist grow or switch to pattern matching?
2. Did credentialed CORS get enabled on new endpoints?

**Core principle**: CORS misconfigurations are LOW by default. Raise severity only when credentials, sensitive data and a secondary weakness line up.

## S: Spend
- Runs in: `railguards-auditor-web`.
- Gate: recon's CORS discovery check is positive.
- Scanners first: Semgrep CORS rules.
- Read: CORS configuration only, then the sensitivity of the endpoints it covers (route list, not handler bodies, unless needed).
- Skip: everything when CORS is absent.
