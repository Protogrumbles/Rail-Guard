---
id: RG-XSS
title: Cross-site scripting and server-side template injection
auditor: web
discovery: The app renders HTML, uses a template engine, or manipulates the DOM.
rules:
  RG-SSTI-001: Server-side template injection
  RG-XSS-001: Stored XSS
  RG-XSS-002: Reflected XSS
  RG-XSS-003: DOM-based XSS
  RG-XSS-004: Unsanitized model output rendered as HTML or Markdown
---

# Cross-Site Scripting and Server-Side Template Injection

## R: Risk First
**Goal**: Detect and prevent script execution in browsers (XSS) and code execution on servers through templates (SSTI).
**Risk**: XSS enables account impersonation, session theft and content injection; SSTI enables remote code execution with application privileges.
**Context**: Web applications that render user-controlled or model-generated content, or that use template engines.

## A: Attached Constraints
- ALWAYS check every user-controlled output variable, and trace it from source to sink, including indirect paths through databases, caches and files.
- ALWAYS use context-appropriate output encoding and framework auto-escaping.
- NEVER assume framework defaults protect you without checking escape hatches.
- NEVER place user data in script blocks, event handlers, CSS, HTML comments, or tag and attribute names.
- NEVER pass user input to template compilation.
- ALWAYS treat LLM output as untrusted HTML; sanitize before rendering Markdown-to-HTML.
- SSTI is CRITICAL; when SSTI and XSS share a path, report SSTI first.

## I: Isolation
- **Trust boundaries**: server rendering, client rendering, and the browser origin.
- **Untrusted inputs**: query and path parameters, form fields, stored user content, URL fragments, `postMessage` data, and model responses.
- **Least privilege**: keep session cookies `HttpOnly`; isolate user-generated HTML in sandboxed iframes or a separate origin when rich content is required.

## L: Local Defaults

**SSTI indicators**: `render_template_string`, `Template(...).render()` (Jinja2), `Environment.from_string`, `compile()`/`evaluate()`/`eval()` (JavaScript templating), `engine.render()`/`process()` (Java: Velocity, FreeMarker, Thymeleaf with user-controlled templates), and string formatting into template source.

**XSS sinks**: `innerHTML`, `outerHTML`, `document.write()`, `insertAdjacentHTML()`, `eval()`, `Function()`, `setTimeout(string)`, Angular `bypassSecurityTrust*`, React `dangerouslySetInnerHTML`, Vue `v-html`, jQuery `html()`/`append()`/`prepend()`, and `marked`/`markdown-it` output inserted without sanitizing.

**Configuration red flags**: `autoescape=False`, `autoescaping: false`, `|safe`, `safe=True`, `mark_safe`, `trust()`, `trusted()`, `raw()`, `Html.Raw`.

**Output encoding by context**:
- HTML body: encode `& < > " '` as entities.
- HTML attribute: always quote; encode as `&#xHH;`.
- JavaScript: only inside quoted strings, `\uXXXX` encoding; prefer passing data via `data-` attributes or JSON script blocks.
- URL: `%HH` encoding; allowlist `http`/`https` schemes for user links.

**Safe DOM manipulation**: `textContent`, `insertAdjacentText`, `createTextNode`.

**Rich text and model output**: sanitize with DOMPurify (browser) or an equivalent allowlist sanitizer server-side, before storage and again at render.

**Classification** (decision tree):
1. Payload saved and served to others → **Stored**. Echoed immediately by the server → **Reflected**. Never reaches the server (fragment, `postMessage`, client source) → **DOM-based**.
2. Edge cases: WebSocket broadcasts are Stored, echoes are Reflected; API-driven content is Stored if persisted; hybrids (stored plus DOM manipulation) are Stored.
3. DOM indicators: `location.hash`, `location.search`, `document.referrer`, `document.URL`, unvalidated `postMessage`, client-side templating in SPAs.

**Severity by type**:
```
IF user input reaches template compilation THEN SSTI, CRITICAL
ELSE IF stored AND (admin interface OR all users) THEN Stored XSS, CRITICAL
ELSE IF stored THEN Stored XSS, HIGH
ELSE IF reflected AND (authenticated area OR sensitive operation) THEN Reflected XSS, HIGH
ELSE IF reflected THEN Reflected XSS, MEDIUM
ELSE IF DOM AND (auth tokens OR critical function) THEN DOM XSS, HIGH
ELSE IF DOM AND complex user interaction required THEN DOM XSS, LOW
ELSE DOM XSS, MEDIUM
```

## G: Generative Path Checks
1. Which template engine is used, and can user input reach template compilation?
2. Is auto-escaping disabled or bypassed anywhere?
3. Does user or model data reach an HTML sink or escape hatch?
4. Is HTML or JavaScript built by concatenation?
5. Does data pass through storage before rendering (stored path)?
6. Are custom rendering helpers escaping correctly?
7. Is rich content sanitized with an allowlist library?
8. Are user-supplied links restricted to safe schemes?

## U: Uncertainty Disclosure
- **Safe default**: if you cannot confirm the escaping configuration, report with `medium` confidence and name the setting to check.
- **Escalate when**: user content is rendered inside privileged origins (admin consoles, internal tools).

## A: Auditability
- **Log**: sanitizer rejections and CSP violation reports if CSP already exists.
- **Comment**: every escape-hatch use must carry a comment naming the sanitizer applied.

## R: Review
1. Did a new escape hatch (`v-html`, `dangerouslySetInnerHTML`, `|safe`) appear?
2. Did a feature start rendering model output or Markdown as HTML?
3. Did a template become user-editable?

**Core principle**: Find SSTI first because it is worse. For XSS, trace every user- or model-controlled value to its sink, rely on auto-escaping, and treat every escape hatch as a finding until a sanitizer is proven.

## S: Spend
- Runs in: `railguards-auditor-web`.
- Gate: recon found HTML rendering, templates or DOM manipulation.
- Scanners first: Semgrep XSS and template-injection rules.
- Read: grep the sinks and red flags above; read only those call sites and the origin of each variable.
- Skip: auto-escaped template output with no escape hatch (false positive).
