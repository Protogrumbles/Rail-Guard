# RAILGUARD Portable - AI-Powered Security Analysis for Cursor

A portable, open-source-friendly security analysis framework that runs inside Cursor IDE. Drop the `.cursor/rules/` directory into any project to get structured, comprehensive security reviews powered by your AI assistant.

## What is RAILGUARD?

RAILGUARD is an 8-pillar security analysis methodology (Risk First, Attached Constraints, Interpretative Framing, Local Defaults, Generative Path Checks, Uncertainty Disclosure, Auditability, Revision + Dialogue) that systematically guides AI assistants through vulnerability detection, severity assessment, and remediation.

Instead of hoping your AI catches security issues, RAILGUARD gives it a structured playbook covering OWASP Top 10, business logic flaws, hardcoded credentials, and more.

## Quick Start

### 1. Copy rules into your project

```bash
cp -r railguard-portable/.cursor/rules/ /path/to/your-project/.cursor/rules/
```

If your project already has a `.cursor/rules/` directory, merge the files. RAILGUARD rules use numbered prefixes to avoid conflicts.

### 2. Trigger a security scan

In Cursor, type any of these in chat:

- "Security audit"
- "Analyze my code for vulnerabilities"
- "Security review"
- "Find security vulnerabilities"
- "Vulnerability assessment"

The AI will follow the RAILGUARD workflow automatically.

### 3. Review the report

Results appear directly in chat, grouped by severity (Critical > High > Medium > Low). Each finding includes:
- Exact file and line location
- Vulnerable code snippet
- Severity with justification
- Remediation steps with secure code examples

## Included Rules

### Always-On Rules (loaded automatically)

| Rule | Purpose |
|------|---------|
| 00-railguard-core | Core methodology and expertise definition |
| 01-security-analysis-trigger | Trigger phrases and workflow initiation |
| 02-input-validation | Input validation and injection prevention |
| 03-authentication | Authentication and session management |
| 07-logic-vulnerability-analysis | Business logic flaws, race conditions, IDOR |
| 12-xss-ssti-detection | XSS and SSTI pattern detection |
| 13-output-format-rules | Report formatting (chat-first, no auto-files) |
| 14-security-analysis-workflow | Step-by-step analysis process |
| 15-standardized-finding-format | Consistent vulnerability reporting structure |
| 16-validation-and-quality-assurance | QA checks for findings accuracy |
| 17-severity-assessment-framework | CIA triad severity scoring |
| 18-code-analysis-focus-areas | OWASP Top 10 analysis checklist |
| 19-language-detection-and-matching | Match remediation to your language/framework |
| 23-hardcoded-credentials-detection | Detect secrets in source code |
| 26-serialization-usage-discovery | Detect serialization for deeper analysis |
| 28-false-positive-and-mitigation-analysis | Eliminate false positives before reporting |
| exclusions | Exclude test files, media, dependencies |

### On-Demand Rules (loaded when relevant)

| Rule | Triggered When |
|------|----------------|
| 04-llm-prompt-injection | LLM/AI integration detected |
| 05-sql-injection-prevention | SQL database usage found |
| 06-xss-prevention | Web app with user content |
| 08-cors-severity-assessment | CORS implementation detected |
| 20-specialized-rule-dispatch | Routes to correct specialized rule |
| 21-xss-type-classification | XSS found, needs type classification |
| 24-registration-auth-context-analysis | Unauthenticated endpoints found |
| 25-deserialization-detection | Serialization usage detected |
| 27-cors-usage-discovery | Checking for CORS presence |

## Complementary Tools

RAILGUARD works best alongside these free tools:

| Tool | What It Does | Install |
|------|-------------|---------|
| Semgrep | Static analysis with 2000+ rules | pip install semgrep, then semgrep scan --config auto |
| gitleaks | Scan git history for leaked secrets | brew install gitleaks or grab the binary |
| trufflehog | Find credentials in repos | brew install trufflehog |
| trivy | Container and dependency CVE scanning | brew install trivy |
| pip-audit | Python dependency vulnerabilities | pip install pip-audit |
| npm audit | Node.js dependency vulnerabilities | Built into npm |

## Customization

### Adding project-specific exclusions

Edit exclusions.mdc to add patterns specific to your project.

### Adding your own remediation docs

Create additional .mdc files in .cursor/rules/ following the RAILGUARD format with R (Risk First), A (Attached Constraints), I (Interpretative Framing), L (Local Defaults), G (Generative Path Checks), U (Uncertainty Disclosure), A (Auditability), and R+D (Revision + Dialogue) sections.

### Adjusting severity thresholds

Edit 17-severity-assessment-framework.mdc to match your risk tolerance.

## How It Works

1. You say "security audit" in Cursor chat
2. Rules activate - the AI loads the workflow and methodology
3. Discovery - maps your codebase, identifies language/framework
4. Detection - runs through mandatory checks (input validation, auth, logic, XSS/SSTI, credentials, serialization, CORS)
5. Specialized analysis - loads additional rules only when relevant vulnerabilities are found
6. False positive filtering - removes framework-mitigated issues, adjusts severity for mitigations
7. Report - presents findings in chat with code, severity, and fix examples

## License

This portable edition is derived from the RAILGUARD security analysis methodology. Use it freely in personal and commercial projects.
