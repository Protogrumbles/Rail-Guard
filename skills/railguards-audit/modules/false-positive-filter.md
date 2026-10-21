---
id: RG-PROC-FP
title: False-positive and mitigation filter
type: procedure
---

# False-Positive and Mitigation Filter

The verifier applies this filter to every candidate finding before the report. Preserve the original list so every decision can be audited.

## Three outcomes

### 1. Remove (false positive)
- Framework protection makes exploitation impossible: auto-escaping (Django, Jinja2 with autoescape, React JSX text, Angular templates, Vue text interpolation); ORM parameterization (Django ORM `filter/get/exclude`, SQLAlchemy ORM, Prisma, Sequelize, TypeORM query builders, Spring Data JPA repository methods); framework CSRF tokens.
- Encrypted or hashed values misidentified as plaintext secrets.
- Managed secrets: environment variable references, secret-manager references (Vault, AWS SSM or Secrets Manager, GCP Secret Manager, Azure Key Vault), CI/CD secret references, placeholders in example configs.
- Test or mock code that never runs in production.
- Misidentification caused by analysis limits (the "sink" is not actually a sink).

### 2. Keep at LOW (real but not exploitable)
- Vulnerable code that is dead, unreachable or unused.
- No input path from any untrusted source.
- Prerequisites cannot be met in the current deployment.
- Best-practice violations with no current exploit path.

### 3. Reduce severity (exploitable with barriers)
Each barrier reduces one level; barriers stack; the minimum is LOW.
- Requires authentication.
- Requires admin access.
- Protected by effective rate limiting.
- Network isolation limits access.
- A human approval step precedes the impactful action (for agent and tool findings).

## Agentic-specific checks

- A prompt-injection finding is **not** a false positive just because the system prompt says "ignore instructions in documents". Prompt-level defenses are not a barrier; only architectural controls (privilege separation, quarantined model, human approval, tool allowlists) count.
- An MCP or tool finding is reduced only if the tool runs in a sandbox or with scoped credentials that actually prevent the impact.
- Hidden Unicode in AI configuration files is never a false positive, even when it appears benign; report at least LOW with the code points.

## Evidence check

For each remaining finding confirm:
1. The snippet matches the stated `file:line` exactly.
2. The full attack chain is traced, or the confidence is lowered and the gap stated.
3. Existing mitigations were searched for (middleware, decorators, validators, framework settings).
4. The remediation fixes the root cause.

## Decision record

Record for each candidate: `REMOVE | KEEP | ADJUST(<from> → <to>)` plus a one-line reason. Show removed findings only if the user asks.

## Principle

When in doubt, report with reduced severity rather than removing. Remove only genuine false positives; never remove a real vulnerability because it is not exploitable today.
