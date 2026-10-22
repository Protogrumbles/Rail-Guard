---
id: RG-SECRET
title: Hardcoded credentials and secret exposure
auditor: secrets
discovery: Always runs.
rules:
  RG-SECRET-001: Hardcoded credential in source or configuration
  RG-SECRET-002: Committed environment file with real values
  RG-SECRET-003: Private key or certificate in the repository
  RG-SECRET-004: Secret placed in an AI context (prompt, AI config, MCP config, agent memory)
---

# Hardcoded Credentials and Secret Exposure

## R: Risk First
**Goal**: Find secrets stored where they can leak, and distinguish them from properly managed references.
**Risk**: Account takeover, cloud compromise, data breach, financial loss.
**Context**: Source code, configuration, infrastructure files, CI workflows, git history, and AI configuration (prompts, `mcp.json`, agent memory).

## A: Attached Constraints
- ALWAYS check whether a value is managed (environment variable, secret manager, placeholder) before flagging.
- NEVER print a full secret in the report; show at most 8 characters followed by `...`.
- ALWAYS flag committed `.env` files with real values as CRITICAL.
- NEVER put secrets in system prompts, model context, or MCP server arguments; pass them through the environment of the process that needs them.

## I: Isolation
- **Trust boundaries**: the repository (readable by every contributor, fork and CI job), container images, client bundles, and model context windows (readable by the model and anything that can inject into it).
- **Untrusted locations**: any file committed to git, front-end bundles, logs, prompts.
- **Least privilege**: scope keys to one service and the minimum permissions; prefer short-lived credentials (OIDC federation, workload identity).

## L: Local Defaults

**Step 1: identify candidates** by key names: `password`, `passwd`, `pwd`, `secret`, `key`, `token`, `apikey`, `api_key`, `api-key`, `access_key`, `secret_key`, `client_secret`, `client_id`, `auth`, `credential`, `cred`, `private_key`, `private`, `cert`, `certificate`; and by value shapes (AWS `AKIA...`, GitHub `ghp_`/`github_pat_`, Slack `xox`, Stripe `sk_live_`, OpenAI `sk-`, Anthropic `sk-ant-`, PEM headers, JWTs).

**Step 2: check management**. Not a vulnerability: `process.env.X`, `os.environ[...]`, `${{ secrets.X }}`, `vault://`, `aws-ssm://`, `gsm://`, `TO_BE_SET`, `CHANGEME`, `your-key-here`, CI variable references. Vulnerability: plaintext real-looking values, base64-encoded credentials, inline connection strings with passwords, private keys.

**Step 3: context**. Test files with obviously fake data: lower. Config files with real-looking values: higher. `.env.example` with placeholders: not a finding. Committed `.env` with real values: CRITICAL.

**AI contexts**: secrets in `mcp.json` `env` or `args`, hardcoded keys in agent code, keys pasted into `AGENTS.md`, prompts or memory files.

**Severity**:
- CRITICAL: production credentials, cloud provider keys (AWS, Azure, GCP), production database passwords, payment API keys, private keys.
- HIGH: non-production credentials, third-party API keys (including LLM provider keys), OAuth client secrets, JWT signing secrets.
- MEDIUM: development or test credentials, local environment credentials, internal service passwords.
- LOW: documented example credentials, placeholders, test fixtures.

## G: Generative Path Checks
1. Are there credential-like keys with literal values?
2. Are those values managed references or placeholders?
3. Are `.env` files, key files or certificates committed?
4. Do AI configuration files or prompts contain secrets?
5. Has a scanner checked git history?

## U: Uncertainty Disclosure
- **Safe default**: if you cannot tell whether a value is real, report it as MEDIUM with `low` confidence and recommend rotation if real.
- **Escalate when**: a secret appears in git history; removal from HEAD is not enough, so recommend rotation.

## A: Auditability
- **Log**: secret-manager access by service identity.
- **Never log**: secret values, even partially beyond 8 characters.

## R: Review
1. Did a new integration add a key to code or config instead of the secret manager?
2. Did a new MCP server get credentials through its arguments?
3. Are scanners running in CI and pre-commit?

**Core principle**: Separate real secrets from managed references by checking context, never echo them, and treat anything committed as compromised.

## S: Spend
- Runs in: `railguards-auditor-secrets`.
- Gate: always.
- Scanners first: gitleaks (history), trufflehog or detect-secrets if present. Triage scanner hits instead of reading files.
- Read: only files with scanner hits or credential-like key names (grep with `-l`, then line ranges).
- Skip: lockfiles, vendored code, binary files.
