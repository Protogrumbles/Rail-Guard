---
id: RG-INPUT
title: Input validation and injection
auditor: web
discovery: Always runs for code that accepts external input (HTTP, CLI, files, queues, model output).
rules:
  RG-INPUT-001: Missing or client-only validation at a trust boundary
  RG-INPUT-002: OS command injection
  RG-INPUT-003: Path traversal
  RG-INPUT-004: Unsafe file upload
  RG-INPUT-005: ReDoS-prone regular expression
  RG-INPUT-006: XML external entity (XXE) processing
  RG-INPUT-007: Server-side request forgery (SSRF)
---

# Input Validation and Injection

## R: Risk First
**Goal**: Prevent injection through validation at every trust boundary.
**Risk**: Command injection, path traversal, malicious uploads, XXE, SSRF, ReDoS and downstream SQL or XSS.
**Context**: User-supplied data, API parameters, file uploads, external feeds, rich content, and output from AI models.

## A: Attached Constraints
- ALWAYS validate input at trust boundaries with both syntactic and semantic checks.
- NEVER rely on client-side validation alone; server-side validation is mandatory.
- ALWAYS prefer allowlists over blocklists.
- NEVER concatenate input into queries, shell commands or file paths.
- ALWAYS validate uploads by content inspection, not only by extension.
- NEVER rely solely on sanitization: validate first, sanitize as defense in depth.
- ALWAYS write ReDoS-resistant, anchored regular expressions.
- ALWAYS encode user-controlled data for its output context before rendering.
- NEVER fetch user-supplied URLs server-side without an allowlist of hosts and schemes.

## I: Isolation
- **Trust boundaries**: network edge, service-to-service calls, queue consumers, file imports, and the boundary between model output and application code.
- **Untrusted inputs**: request bodies, query strings, headers, cookies, uploaded files, webhook payloads, third-party API responses, and anything an LLM generated.
- **Least privilege**: run shell-outs as unprivileged users; store uploads outside the web root; give URL fetchers no access to internal networks or cloud metadata endpoints (`169.254.169.254`).

## L: Local Defaults

**When handling form submissions**:
- Validate format (syntactic) and business correctness (semantic), with length limits.
- Return clear errors that do not reveal internals; use established validation libraries.

**When processing API requests**:
- Validate against a schema (JSON Schema, Pydantic, Zod, Bean Validation), recursively for nested objects and arrays.
- Enforce request size limits and rate limiting.

**When running system commands**:
- Avoid the shell: pass an argument array (`subprocess.run([...], shell=False)`, `execFile`, `ProcessBuilder`).
- Allowlist any user-influenced argument; prefix filenames with `--` or `./` to stop option injection.

**When building file paths**:
- Resolve the canonical path and verify it stays inside the intended base directory; reject `..`, absolute paths and NUL bytes.

**When handling file uploads**:
- Check magic numbers, enforce size limits, scan for malware, store with randomized names outside the web root, and re-encode images to strip payloads.

**When parsing XML**:
- Disable DTDs and external entities (`defusedxml` in Python; `disallow-doctype-decl` in Java).

**When fetching URLs**:
- Allowlist schemes and hosts, resolve DNS once and block private, loopback and link-local ranges, and disable redirects or re-validate each hop.

**When processing Unicode**:
- Normalize (NFC or NFKC), allowlist character categories, and guard identifiers against homographs.

**When validating email addresses**:
- Basic syntax check, then ownership verification by token; enforce 64-character local part and 254-character total limits.

## G: Generative Path Checks
1. Are all input sources (forms, APIs, files, feeds, model output) identified and validated?
2. Is validation server-side with safe error handling?
3. Are both syntactic and semantic checks present?
4. Are shell calls made without a shell and with allowlisted arguments?
5. Are file paths canonicalized and confined to a base directory?
6. Are uploads validated by content and stored safely?
7. Are regular expressions anchored and free of nested quantifiers on user input?
8. Are XML parsers configured to reject external entities?
9. Are server-side URL fetches restricted to allowlisted destinations?
10. Are length and range limits enforced?

## U: Uncertainty Disclosure
- **Safe default**: if the expected format is unknown, apply a strict allowlist and a length limit, and flag the assumption.
- **Escalate when**: input reaches a shell, an interpreter (`eval`), or a URL fetcher and you cannot confirm the allowlist; or the validation lives in a component you cannot see.
- Mark findings `medium` confidence when validation might exist in middleware that is not in scope.

## A: Auditability
- **Log**: validation failures with field name and rule (not the raw value), rejected uploads, blocked SSRF destinations.
- **Never log**: raw payloads containing credentials, tokens or PII.
- **Comment**: at each shell-out or dynamic path, state why the input is safe.

## R: Review
1. Did a new endpoint, consumer or tool add an input source without a schema?
2. Did a refactor move validation behind a path that can now be bypassed?
3. Are model outputs treated as untrusted input everywhere they are used?

**Core principle**: Never trust input from outside the trust boundary, including model output. Validate on the server with allowlists, keep data out of code positions, and confine every file, command and network access to what is expected.

## S: Spend
- Runs in: `railguards-auditor-web`.
- Gate: always, but only for in-scope files with external input.
- Scanners first: Semgrep rules for command injection, path traversal, SSRF and XXE; triage their hits before manual review.
- Read: handlers, their validators, and the sink call sites (line ranges). Grep sinks: `subprocess`, `exec(`, `system(`, `child_process`, `Runtime.exec`, `open(`, `readFile`, `requests.get`, `fetch(`, `urlopen`, `XMLParser`, `DocumentBuilder`.
- Skip: test fixtures, generated clients, vendored code.
