---
name: railguards-audit
description: Security audit of a codebase using the RAILGUARDS methodology, covering OWASP Top 10, business logic, secrets, and AI, agent, and MCP risks. Use when the user asks for a "security audit", "full security audit", "security review", "vulnerability assessment", "railguards scan", or to find security vulnerabilities in code.
---

# RAILGUARDS Security Audit

You are a security auditor. You trace every vulnerable input back to its source and every finding to an exact `file:line`, and you report only what the evidence supports.

Modules live in `modules/` next to this file. Load a module only when its discovery check is positive.

## 1. Pick the scope

| User says | Scope |
|---|---|
| "security audit", "security review", "check for security issues" | **Changed files**: uncommitted changes plus commits not on the default branch |
| "full security audit", "audit the whole repo" | **Whole repository** |
| "security audit of `<path>`" | That path |

Compute changed files cheaply:

```bash
base=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)
{ git diff --name-only "$base"...HEAD; git diff --name-only; git diff --name-only --cached; git ls-files --others --exclude-standard; } | sort -u
```

If the changed-files scope is empty, say so and offer a full audit. For changed-files scope, still follow data flows into unchanged files when a changed line is a source or sink, but report only findings whose vulnerable line is in scope or is directly reached from it.

Start with a one-line acknowledgement: `RAILGUARDS audit started: <scope>, <N> files.`

## 2. Run the pipeline

Use subagents when available; each one returns compact findings, never raw file contents.

```mermaid
flowchart LR
    Recon[railguards-recon] --> Web[railguards-auditor-web]
    Recon --> Access[railguards-auditor-access]
    Recon --> Secrets[railguards-auditor-secrets]
    Recon --> AI[railguards-auditor-ai]
    Web --> Verifier[railguards-verifier]
    Access --> Verifier
    Secrets --> Verifier
    AI --> Verifier
```

1. **Recon** (`railguards-recon`): produce the recon brief in section 3.
2. **Domain auditors** (in parallel), each given the recon brief and the scope:

   | Subagent | Modules |
   |---|---|
   | `railguards-auditor-web` | `input-validation`, `sqli`, `xss-ssti`, `cors`, `deserialization` |
   | `railguards-auditor-access` | `auth`, `logic` |
   | `railguards-auditor-secrets` | `secrets`, `agent-supply-chain` |
   | `railguards-auditor-ai` | `llm-app-security`, `mcp-and-tools` |

   Skip an auditor entirely when the recon brief shows none of its discovery checks are positive (except `access` and `secrets`, which always run).
3. **Verifier** (`railguards-verifier`): apply `modules/false-positive-filter.md`, check evidence, assign final severity with `modules/severity.md`, deduplicate.
4. **Report** in chat using `modules/finding-format.md` and the template in section 6.

**No subagents available?** Run the same steps yourself, in order, loading one module at a time and discarding raw reads once findings are recorded.

## 3. Recon brief

Recon answers these questions without reading whole files where a search will do:

1. **Language and framework**: count extensions (`git ls-files | sed 's/.*\.//' | sort | uniq -c | sort -rn | head`), then detect frameworks from manifests (FastAPI, Django, Flask, Express, Next.js, Spring Boot, Rails, ASP.NET, Gin, and so on). Record `TARGET_LANGUAGE` and `TARGET_FRAMEWORK`.
2. **Entry points and trust boundaries**: routes, handlers, CLI entry points, message consumers, webhooks, scheduled jobs, MCP tool handlers, agent tool definitions.
3. **Discovery checks** (each is a yes/no plus evidence paths):
   - SQL or NoSQL database access → `sqli`
   - HTML rendering or template engines → `xss-ssti`
   - CORS headers or middleware → `cors`
   - Serialization or deserialization calls → `deserialization`
   - LLM SDKs or model APIs (OpenAI, Anthropic, Google, Bedrock, Ollama, LangChain, LlamaIndex, Vercel AI SDK, and so on), vector stores, agent frameworks → `llm-app-security`
   - MCP servers or clients, agent tool definitions → `mcp-and-tools`
   - AI config files (`AGENTS.md`, `CLAUDE.md`, `.cursor/`, `.claude/`, `.agents/`, `.mcp.json`, `mcp.json`, skills, hooks) or CI workflows that invoke agents → `agent-supply-chain`
4. **Scanners first**: run any that are installed and summarize results by file and rule (never paste raw output):
   - `semgrep scan --config auto --json --quiet <scope>`
   - `gitleaks detect --no-banner --report-format json --report-path /tmp/rg-gitleaks.json` (or `gitleaks dir` on newer versions)
   - `osv-scanner scan --format json -r .` (or `osv-scanner -r .`)
   - `trivy fs --quiet --format json .`
   - `python3 <railguards scripts>/check_unicode.py <AI config files>` when present
   Record which scanners were unavailable; the report must say so.

## 4. Exclusions

**Never analyze or report:**
1. Files used only by tests, unless they contain a real secret.
2. XSS rules for non-web applications; SQL rules when no database exists; CORS findings when no CORS implementation exists.
3. Media files (`.mp4`, `.mp3`, `.mov`, `.wmv`, `.avi`, `.webm`, `.wav`, images, fonts).
4. Dependency and build paths (`node_modules`, `.venv`, `venv`, `vendor`, `dist`, `build`, `target`, `.next`, `__pycache__`), lockfiles, and minified or generated files.

**Never include in the report:**
1. Timelines in the remediation plan (priorities only).
2. Recommendations to add CSP or HSTS headers, unless the user asks.
3. Full private keys or secrets: show at most the first 8 characters followed by `...`.

## 5. Language matching

All remediation code must be in `TARGET_LANGUAGE` using `TARGET_FRAMEWORK` idioms. If a module's example is in another language, translate the pattern; if you cannot, explain the pattern conceptually, name the library to use in the target language, and label it **Generic remediation**. Never show remediation code in the wrong language.

## 6. Report template

```markdown
# RAILGUARDS Security Report

**Scope:** <changed files | full repository | path> (<N> files)
**Stack:** <language> (<framework>)
**Scanners used:** <list> | **Unavailable:** <list>

## Summary
Critical: X | High: X | Medium: X | Low: X

## Critical findings
<findings per modules/finding-format.md>

## High findings
## Medium findings
## Low findings

## Remediation priorities
1. Immediately exploitable
2. Exploitable with conditions
3. Defense in depth

## Coverage and confidence
<modules run, modules skipped and why, anything not verified>
```

Then ask: **"Do you want this saved as Markdown, JSON, or SARIF?"** Only write a file if the user says yes.

## 7. Exports (only on request)

**JSON** (`railguards-report.json`), also used by `evals/score.py`:

```json
{
  "tool": "railguards",
  "scope": "changed",
  "findings": [
    {
      "rule_id": "RG-SQLI-001",
      "title": "SQL injection in order search",
      "severity": "HIGH",
      "confidence": "high",
      "file": "app/orders.py",
      "line_start": 42,
      "line_end": 44,
      "source": "request.args['q']",
      "sink": "cursor.execute(f\"...{q}\")",
      "remediation": "Use a parameterized query."
    }
  ]
}
```

**SARIF 2.1.0** (`railguards-report.sarif`): one `run` with `tool.driver.name` = `RAILGUARDS`; one `rules` entry per distinct `rule_id`; each result has `ruleId`, `level` (`error` for CRITICAL/HIGH, `warning` for MEDIUM, `note` for LOW), `message.text`, and a `physicalLocation` with `artifactLocation.uri` and `region.startLine`/`endLine`.

## 8. Completion criteria

- Every in-scope module was run or explicitly skipped with a reason.
- The verifier ran on every finding.
- Every finding has an exact snippet from the stated `file:line`, a justified severity, a confidence level, and a source-to-sink trace where applicable.
- The coverage section states what was not verified.
