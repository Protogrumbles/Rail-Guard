# Migrating from RAILGUARD v1 to RAILGUARDS

RAILGUARD v1 was 26 Cursor rule files copied into `.cursor/rules/`. Seventeen of them had `alwaysApply: true`, so about 10,500 tokens of security methodology loaded into every request, even when you were not auditing anything. The last v1 commit is tagged [`v1-legacy`](https://github.com/Protogrumbles/Rail-Guard/tree/v1-legacy).

RAILGUARDS keeps all of v1's detection knowledge and moves it into an on-demand skill. Only a short guardrail block stays always-on: about 1,050 tokens including skill descriptions, measured with `scripts/measure_overhead.py`.

## Upgrade a project

1. Delete the v1 rule files from the project's `.cursor/rules/` (keep any rules of your own):

   ```bash
   cd your-project/.cursor/rules
   rm -f 00-railguard-core.mdc 01-security-analysis-trigger.mdc 02-input-validation.mdc \
     03-authentication.mdc 04-llm-prompt-injection.mdc 05-sql-injection-prevention.mdc \
     06-xss-prevention.mdc 07-logic-vulnerability-analysis.mdc 08-cors-severity-assessment.mdc \
     12-xss-ssti-detection.mdc 13-output-format-rules.mdc 14-security-analysis-workflow.mdc \
     15-standardized-finding-format.mdc 16-validation-and-quality-assurance.mdc \
     17-severity-assessment-framework.mdc 18-code-analysis-focus-areas.mdc \
     19-language-detection-and-matching.mdc 20-specialized-rule-dispatch.mdc \
     21-xss-type-classification.mdc 23-hardcoded-credentials-detection.mdc \
     24-registration-auth-context-analysis.mdc 25-deserialization-detection.mdc \
     26-serialization-usage-discovery.mdc 27-cors-usage-discovery.mdc \
     28-false-positive-and-mitigation-analysis.mdc exclusions.mdc
   ```

   The installer warns if any of these files are still present.

2. Run the installer from a RAILGUARDS checkout: `scripts/install.sh /path/to/your-project`.
3. If you customized v1 files, port the changes to the locations in the table below. Exclusions now live in section 4 of `railguards-audit/SKILL.md`; severity thresholds in `modules/severity.md`.

"Security audit" still starts an audit. It now covers changed files by default; say "full security audit" for the whole repository.

## Where each v1 rule went

Module paths are relative to `skills/railguards-audit/`.

| v1 rule | RAILGUARDS location |
|---|---|
| `00-railguard-core` | `core/pillars.md` (methodology and module template) and `AGENTS.md` (always-on guardrails) |
| `01-security-analysis-trigger` | `AGENTS.md` Triggers section and `SKILL.md` section 1 (scope) |
| `02-input-validation` | `modules/input-validation.md` |
| `03-authentication` | `modules/auth.md` |
| `04-llm-prompt-injection` | `modules/llm-app-security.md`, expanded to the OWASP LLM Top 10 (2025) and Agentic Top 10 (2026) |
| `05-sql-injection-prevention` | `modules/sqli.md` |
| `06-xss-prevention` | `modules/xss-ssti.md` |
| `07-logic-vulnerability-analysis` | `modules/logic.md` |
| `08-cors-severity-assessment` | `modules/cors.md` |
| `12-xss-ssti-detection` | `modules/xss-ssti.md` |
| `13-output-format-rules` | `modules/finding-format.md` (output rules) and `SKILL.md` sections 6 and 7 (chat report; files only on request) |
| `14-security-analysis-workflow` | `SKILL.md` section 2 (recon, parallel auditors, verifier) |
| `15-standardized-finding-format` | `modules/finding-format.md` |
| `16-validation-and-quality-assurance` | `modules/false-positive-filter.md` and the finding-format pre-flight check |
| `17-severity-assessment-framework` | `modules/severity.md` |
| `18-code-analysis-focus-areas` | `SKILL.md` section 3 (recon discovery checks) and the detection modules |
| `19-language-detection-and-matching` | `SKILL.md` section 5 (language matching) |
| `20-specialized-rule-dispatch` | `SKILL.md` sections 2 and 3 (discovery checks pick the modules) |
| `21-xss-type-classification` | `modules/xss-ssti.md` |
| `23-hardcoded-credentials-detection` | `modules/secrets.md` |
| `24-registration-auth-context-analysis` | `modules/auth.md` |
| `25-deserialization-detection` | `modules/deserialization.md` |
| `26-serialization-usage-discovery` | `modules/deserialization.md` (discovery) and the recon `serialization` check |
| `27-cors-usage-discovery` | `modules/cors.md` (discovery) and the recon `cors` check |
| `28-false-positive-and-mitigation-analysis` | `modules/false-positive-filter.md` |
| `exclusions` | `SKILL.md` section 4 |

## What changed in the methodology

- **Pillars:** RAILGUARD's eight pillars became nine. Interpretative Framing became **Isolation** (trust boundaries, untrusted content, least privilege); Revision + Dialogue became **Review**; **Spend** is new (who runs the module, what it may read, how it stays cheap). See `core/pillars.md`.
- **Findings** keep the v1 structure and add a stable rule ID (for example `RG-SQLI-001`), a confidence level, a source-to-sink trace, and an agentic blast-radius note. Severity adds a blast-radius factor that can raise an AI finding one level.
- **New modules:** `mcp-and-tools` (tool poisoning, rug pulls, confused deputy, local server exposure) and `agent-supply-chain` (hidden Unicode in rules files, unpinned MCP servers, slopsquatting, agent CI workflows).
- **New skills:** `railguards-vet` (vet packages, MCP servers, skills, and hooks before use) and `railguards-token-plan` (reduce token usage, with before-and-after measurement).
- **Hooks:** a single engine (`hooks/guard.py`) enforces the highest-risk guardrails in Cursor and Claude Code, so they no longer depend on the model following prose.
- **Claude Code** is supported alongside Cursor.
