---
id: RG-SUPPLY
title: Agent configuration and supply chain
auditor: secrets
discovery: AI config files (AGENTS.md, CLAUDE.md, .cursor/, .claude/, .agents/, mcp.json, .mcp.json, skills, hooks), dependency manifests, or CI workflows that invoke agents are present.
rules:
  RG-SUPPLY-001: Hidden or bidirectional Unicode in AI configuration (rules file backdoor) [ASI04]
  RG-SUPPLY-002: Instructions in AI configuration that weaken controls or exfiltrate data [ASI01, ASI04]
  RG-SUPPLY-003: MCP configuration runs unpinned or unverified packages (npx -y, uvx, latest) [ASI04]
  RG-SUPPLY-004: Secrets embedded in AI or MCP configuration [ASI03]
  RG-SUPPLY-005: Hooks or skills that execute remote or unreviewed scripts [ASI04, ASI05]
  RG-SUPPLY-006: Hallucinated or typosquatted dependency (slopsquatting) [LLM03, ASI04]
  RG-SUPPLY-007: CI workflow feeds untrusted issue, PR, or comment text to an agent with write access or secrets [ASI01, ASI03]
  RG-SUPPLY-008: Auto-approval settings that let agents run commands or tools without review [ASI02, ASI09]
---

# Agent Configuration and Supply Chain

## R: Risk First
**Goal**: Treat the repository's AI configuration and dependencies as code that can be attacked.
**Risk**: A poisoned rule file, skill, hook or MCP config silently changes what every developer's agent does; a hallucinated package name installs attacker code; a CI agent triggered by an outsider's issue leaks secrets or pushes code.
**Context**: `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/`, `.cursor/hooks.json`, `.cursor/mcp.json`, `.claude/settings*.json`, `.mcp.json`, `.agents/skills/`, `.claude/skills/`, `.claude/agents/`, `.cursor/agents/`, dependency manifests, and CI workflows (GitHub Actions, GitLab CI) that run coding agents.

## A: Attached Constraints
- NEVER allow invisible or bidirectional Unicode in AI configuration, skills, hooks or tool metadata.
- NEVER allow AI configuration to instruct agents to skip reviews, disable security controls, hide actions from the user, or send data to external endpoints.
- ALWAYS pin MCP server packages to exact versions (or digests for containers); NEVER use `@latest` or unversioned `npx -y` / `uvx` in shared configs.
- NEVER commit secrets in MCP configs; reference environment variables.
- NEVER let hooks or skills download and execute remote scripts.
- ALWAYS verify that new dependencies exist, are the intended package, and are maintained.
- NEVER run an agent with write tokens or secrets on untrusted event text (`issues`, `issue_comment`, `pull_request_target`) without isolation and approval.
- NEVER commit auto-approve settings that allow arbitrary shell commands or all MCP tools.

## I: Isolation
- **Trust boundaries**: the repository's AI config is executed with each developer's privileges; CI agents run with the workflow's token and secrets; package registries are outside your control.
- **Untrusted inputs**: AI config from forks or external PRs, third-party skills and rules, MCP packages, issue and PR text, comments, commit messages, and package names suggested by a model.
- **Least privilege**: CI agents get read-only tokens by default (`permissions: contents: read`), no secrets on untrusted triggers, and write access only through a separate, approved job.

## L: Local Defaults

**When reviewing AI config files**:
- Run `python3 scripts/check_unicode.py <files>`; any finding in these files is reportable.
- Read the instructions as an attacker would: look for "do not tell the user", "always run", "ignore previous", external URLs, base64 blobs, or commands that fetch and execute.

**When reviewing MCP configs** (`mcp.json`, `.mcp.json`, `.cursor/mcp.json`, Claude settings):
- Packages pinned (`"args": ["-y", "@scope/server@1.4.2"]`), containers by digest, remote servers over HTTPS from known publishers, secrets via `${env:VAR}` or the host's secret mechanism.

**When reviewing hooks and skills**:
- Scripts are in the repo and reviewed; no `curl | sh`, no network fetch of code; hooks fail safely.

**When reviewing dependencies** (including ones an agent added):
- Confirm each new name exists in the registry and matches the intended project (homepage, repository, maintainers); compare against popular names for one-character differences, swapped separators (`-` vs `_`), or added words (`-utils`, `-js`, `py-`); check age and download counts; look for install scripts (`preinstall`, `postinstall`, `setup.py` side effects).

**When reviewing CI workflows that run agents**:
- Avoid `pull_request_target` and `issue_comment` triggers with checked-out PR code or secrets; set minimal `permissions`; never interpolate `${{ github.event.issue.title }}` or `body` directly into prompts or shell; require maintainer approval (labels, environments) before an agent can push.

**When reviewing auto-approval settings**:
- No wildcard shell allowlists (`Bash(*)`, "run everything"), no blanket MCP auto-approval in committed config.

## G: Generative Path Checks
1. Do AI config files, skills, hooks or tool metadata contain hidden Unicode?
2. Do they contain instructions to hide actions, skip review, disable controls or contact external endpoints?
3. Are MCP packages pinned and from verified publishers?
4. Are secrets absent from AI and MCP configs?
5. Do hooks or skills fetch and execute remote code?
6. Does every new dependency exist, match its intended project, and look healthy?
7. Do CI agents on untrusted triggers run without secrets and with read-only tokens?
8. Are committed auto-approval settings narrow?

## U: Uncertainty Disclosure
- **Safe default**: unknown publishers, unpinned packages and unexplained instructions are findings until explained.
- **Escalate when**: hidden Unicode or exfiltration instructions are found (possible active compromise): recommend checking git blame and rotating any credentials the agent could reach.

## A: Auditability
- **Log**: changes to AI config files through code review (CODEOWNERS on `.cursor/`, `.claude/`, `.agents/`, `AGENTS.md`), MCP lock drift, hook decisions (`.railguards/audit-log.jsonl`).
- **Comment**: each MCP server entry should state its purpose and approver.

## R: Review
1. Did a PR modify AI config, skills, hooks or MCP config? Require code-owner review.
2. Did an agent add dependencies in this change? Re-vet them.
3. Did a workflow add a new trigger or permission?

**Core principle**: Your agent's configuration is executable code with your privileges. Pin it, review it, scan it for hidden text, and never let untrusted text steer an agent that holds secrets or write access.

## S: Spend
- Runs in: `railguards-auditor-secrets`.
- Gate: recon's AI-config discovery check is positive, or manifests changed in scope.
- Scanners first: `scripts/check_unicode.py`, osv-scanner on manifests, gitleaks on config files.
- Read: AI config files in full (they are short), manifest diffs (not lockfiles), workflow files that mention agents.
- Skip: unchanged manifests in changed-files scope.
