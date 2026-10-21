# RAILGUARDS

Security guardrails and token discipline for AI coding agents, for Cursor and Claude Code.

RAILGUARDS has two layers:

1. **Always-on guardrails:** a short block in `AGENTS.md` (31 lines) plus hooks that enforce the riskiest cases. It covers agent security (untrusted content, secrets, dependencies, irreversible actions, MCP tools) and spend habits (search before reading, delegate exploration, keep output small).
2. **On-demand skills** that load only when needed:
   - `railguards-audit`: a structured security audit run by subagents. Recon runs first, then four domain auditors in parallel, then a verifier.
   - `railguards-token-plan`: diagnoses where your agent wastes tokens, recommends fixes layer by layer (subagents, code graphs, memory, ignore files), scaffolds them, and measures the before-and-after fixed overhead.
   - `railguards-vet`: vets a package, MCP server, skill, rule file, or hook before your agent installs or uses it.

RAILGUARDS replaces RAILGUARD v1, whose 26 rule files loaded about 10,500 tokens into every request. A RAILGUARDS install adds about 1,050 tokens per request (always-on block plus skill descriptions), and the detection depth moved into the audit skill. See [MIGRATION.md](MIGRATION.md).

## Quick start

Requires Python 3.9 or newer (the hooks run on it; standard library only).

```bash
git clone https://github.com/Protogrumbles/Rail-Guard.git railguards
railguards/scripts/install.sh /path/to/your-project            # detects Cursor and/or Claude Code
railguards/scripts/install.sh /path/to/your-project --tool both --profile strict
```

Restart the agent, then try it:

| Say | What happens |
|---|---|
| "security audit" | Audits changed files (uncommitted changes plus commits not on the default branch) |
| "full security audit" | Audits the whole repository |
| "token plan" or "reduce token usage" | Diagnoses token waste, plans, scaffolds after you confirm, then measures |
| "vet this package / MCP server / skill" | Returns **Allow**, **Allow with conditions**, or **Reject** with reasons |

Findings appear in chat, grouped by severity, each with a rule ID, a confidence level, a source-to-sink trace, and remediation in your project's language. A Markdown, JSON, or SARIF file is written only if you ask.

### Installer options

| Option | Effect |
|---|---|
| `--tool auto\|cursor\|claude\|both` | Which tool to configure. `auto` (default) looks for `.cursor/`, `.claude/`, or `CLAUDE.md`, and falls back to Cursor. |
| `--profile ask\|strict` | `ask` (default) pauses risky actions for approval. `strict` blocks the highest-risk ones and makes Cursor's permission hooks fail closed. |
| `--core agents-md\|cursor-rule` | Where the always-on block goes. Claude Code always uses `AGENTS.md` (imported from `CLAUDE.md`). |
| `--no-hooks` | Install rules and skills only |
| `--uninstall` | Remove everything RAILGUARDS added; your own content and `.railguards/` data files stay |

The installer never overwrites your content: Markdown changes live between `<!-- RAILGUARDS:BEGIN -->` and `<!-- RAILGUARDS:END -->`, and JSON hook configs are merged. Re-running it upgrades in place.

### What gets installed

| Piece | Cursor | Claude Code |
|---|---|---|
| Always-on block | `AGENTS.md` (or `.cursor/rules/railguards.mdc`) | `AGENTS.md` plus an `@AGENTS.md` import in `CLAUDE.md` |
| Skills | `.agents/skills/railguards-*` | `.claude/skills/railguards-*` (Cursor reads these too) |
| Subagents | `.cursor/agents/railguards-*.md` | `.claude/agents/railguards-*.md` (recon runs on Haiku) |
| Hooks | `.cursor/hooks.json` | `.claude/settings.json` |
| Hook engine, scripts, config | `.railguards/` | `.railguards/` |

## Hooks

One engine, `hooks/guard.py`, applies the same policy in both tools.

| Event | Ask profile (default) | Strict profile |
|---|---|---|
| Shell: `curl \| sh`, `rm -rf` on root, home, or the current directory, destructive SQL, reading secrets through the shell, force push to a protected branch | Ask | Deny |
| Shell: other force pushes, `git reset --hard`, deploys, publishes, infrastructure changes | Ask | Ask |
| Shell: installing a new package | Ask, with a reminder to run `railguards-vet` | Same |
| Reading a likely secret file (`.env`, keys, cloud credentials) | Claude Code asks. Cursor cannot ask on reads, so it blocks and explains how to allow the file. | Deny |
| After a file edit | Reports hidden Unicode and likely secrets to the agent | Same |
| After an MCP tool call | Appends server, tool, duration, and an input hash to `.railguards/audit-log.jsonl` (never raw results) | Same |

To let agents read a specific file that looks like a secret (for example a test fixture), add its path or glob to `.railguards/allow-read`. To change the profile, edit `.railguards/config.json` or set `RAILGUARDS_PROFILE`. Internal hook errors fail open, so a broken hook never blocks your agent.

## The RAILGUARDS pillars

Every audit module answers the same nine questions, in order ([core/pillars.md](core/pillars.md)):

| | Pillar | Question |
|---|---|---|
| R | Risk First | What goal, risk, and context does this module address? |
| A | Attached Constraints | What must ALWAYS or NEVER happen? |
| I | Isolation | Where are the trust boundaries, what is untrusted, and what privilege does each component get? |
| L | Local Defaults | What does the secure implementation look like? |
| G | Generative Path Checks | Which verifiable checks confirm the code is safe? |
| U | Uncertainty Disclosure | What is the safe default when requirements are unclear, and when should this escalate? |
| A | Auditability | What should be logged so behavior can be reconstructed? |
| R | Review | Which questions keep this safe over time? |
| S | Spend | Who runs this module, what may they read, and how do they keep it cheap? |

Audit modules: input validation, SQL injection, authentication, business logic, XSS and SSTI, CORS, deserialization, secrets, LLM application security (OWASP LLM Top 10 2025 and Agentic Top 10 2026), MCP and tools, and agent supply chain. Severity, finding format, and false-positive filtering are shared procedure modules.

## Optional tools

The audit runs these when they are installed and triages their output instead of reading every file: [Semgrep](https://semgrep.dev), [gitleaks](https://github.com/gitleaks/gitleaks), [osv-scanner](https://github.com/google/osv-scanner), [trivy](https://github.com/aquasecurity/trivy). With [tiktoken](https://github.com/openai/tiktoken) installed, `measure_overhead.py` counts tokens exactly instead of estimating four characters per token.

Helper scripts (copied to `.railguards/scripts/`):

- `measure_overhead.py [--save-baseline | --compare]`: fixed context overhead per request, per tool.
- `check_unicode.py PATH...`: finds hidden and bidirectional characters (rules-file backdoors).
- `mcp_lock.py snapshot|verify [--probe]`: pins MCP server configs and tool definitions in `.railguards/mcp-lock.json` and reports drift (rug pulls).

## Repository layout

```
AGENTS.md                 always-on block (the source the installer copies)
core/pillars.md           pillar definitions and the module template
skills/                   railguards-audit (with modules/), railguards-token-plan, railguards-vet
hooks/guard.py            hook engine for both tools
scripts/                  installer, measurement, Unicode scanner, MCP lock, CI checks
adapters/                 Cursor and Claude Code subagents, hooks, rule mirror, CLAUDE.md import
evals/                    vulnerable fixtures with expected findings, scorer, guardrail scenarios
tests/                    unit tests
docs/superpowers/         design spec and implementation plan
```

## Development

```bash
python3 -m unittest discover -s tests      # unit tests
python3 scripts/ci_checks.py               # always-on budget, hidden Unicode, pillars, adapter mirrors
shellcheck scripts/*.sh
```

CI runs all three. The always-on block is limited to 60 lines and 1,200 estimated tokens. The Cursor and Claude Code subagents must keep identical bodies. `adapters/cursor/rules/railguards.mdc` must match the `AGENTS.md` block.

To measure audit quality, run an audit on a copy of a fixture and score the JSON export; see [evals/README.md](evals/README.md).

## License

Derived from the RAILGUARD security analysis methodology. Use it freely in personal and commercial projects.
