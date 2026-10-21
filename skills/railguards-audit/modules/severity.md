---
id: RG-PROC-SEVERITY
title: Severity assessment
type: procedure
---

# Severity Assessment

Assign severity in four steps: CIA impact, information-disclosure logic, contextual adjustment, then the agentic blast-radius factor. Always write a one-sentence justification.

## 1. CIA triad impact

**Confidentiality**
- HIGH: API keys, passwords, cryptographic secrets, session tokens, PII, financial data
- MEDIUM: user account info, internal architecture, configuration details, error messages revealing internals
- LOW: software versions, general system information, non-sensitive operational data

**Integrity**
- HIGH: modify critical business data, alter authentication, inject code or commands
- MEDIUM: modify user data, alter non-critical settings, inject content in user-facing areas
- LOW: modify non-critical display elements or temporary data

**Availability**
- HIGH: complete outage, resource exhaustion, crash of critical services, unbounded model spend
- MEDIUM: partial degradation, specific user groups affected, temporary interruption
- LOW: minimal performance impact, single sessions only

## 2. Information disclosure

**Access vector**
- Source code disclosure (requires repo or filesystem access): reduce one level.
- Application disclosure (reachable through normal use): keep severity.
- Public disclosure (no authentication): keep or raise.

**By information type**
- CRITICAL: API keys, database credentials or auth tokens in public responses
- HIGH: API keys in authenticated responses; cloud credentials in app-accessible locations
- MEDIUM: API keys in source code; PII in error messages; internal architecture in responses
- LOW: versions in headers; general system info; non-sensitive configuration

## 3. Vulnerability-specific anchors

**XSS**: CRITICAL stored XSS in admin or user-management panels. HIGH DOM XSS in authenticated areas, reflected XSS with session access, stored XSS in user content. MEDIUM reflected XSS in public forms, DOM XSS in non-sensitive areas. LOW XSS in error pages, self-XSS.

**SSTI**: CRITICAL by default (server-side code execution).

**SQL injection**: CRITICAL public endpoint with full DB access, union-based with sensitive data. HIGH authenticated endpoint with user data, boolean-based blind. MEDIUM admin endpoint with limited access, time-based blind. LOW internal read-only tool, non-sensitive data only.

**Authentication and authorization**: CRITICAL complete bypass, admin privilege escalation. HIGH user privilege escalation, session flaws enabling account takeover. MEDIUM IDOR on sensitive but non-critical data, weak auth with other barriers. LOW IDOR on non-sensitive data, insider-only weaknesses.

**Deserialization**: CRITICAL native serialization with untrusted input, exposed RMI/JMX/T3, type-enabled JSON/XML. HIGH behind authentication, unsafe custom `readObject`. MEDIUM with class filtering, internal-only. LOW strict allowlists, no known gadgets.

**CORS**: LOW by default; see `cors.md` for the conditions that raise it.

**Prompt injection and agent tools**: see the blast-radius factor below; the lethal trifecta is HIGH at minimum.

## 4. Contextual adjustment

- Public exposure, no auth: keep or raise.
- Authenticated, limited roles: keep.
- Internal network or admin only: consider reducing.
- Trivial or automatable exploitation: keep or raise.
- Multiple conditions or significant user interaction: consider reducing.

## 5. Agentic blast-radius factor

For findings on a path an AI agent or model output can drive, raise severity **one level** (maximum CRITICAL) when two or more of these hold:
- the agent acts **autonomously** (no human approval before the impactful action);
- the agent holds **broad privileges** (write access to repos, production data, payment or messaging APIs, shell);
- the agent has **external reach** (can send data or messages outside the trust boundary);
- the agent processes **untrusted content** in the same context as the above.

State the factor explicitly in the finding: `Blast radius: autonomous + shell + external reach (raised one level)`.

## 6. Output

`Severity: HIGH (public endpoint, union-based SQLi exposing customer PII; blast radius n/a)`
