---
id: RG-PROC-FORMAT
title: Finding format and output rules
type: procedure
---

# Finding Format and Output Rules

## Output rules

1. **Chat first.** Display every finding in the chat. Never create report files automatically.
2. **Ask before writing files.** After the report, ask whether to save it as Markdown, JSON or SARIF.
3. **Large reports** still go to chat; offer a file because of size. With more than 10 findings, group by severity and keep LOW findings to one line each unless asked.
4. **Code examples** stay inline; do not create separate remediation files unless asked.

## Finding structure

Every finding uses exactly this structure:

````markdown
### <N>. <Vulnerability title>

**Rule**: `<RULE_ID>` | **Severity**: <CRITICAL|HIGH|MEDIUM|LOW> | **Confidence**: <high|medium|low>
**Location**: `<file>:<line_start>-<line_end>` in `<function or endpoint>`
**Description**: <exactly one sentence: what it is and why it is dangerous>
**Trace**: <source> → <intermediate steps> → <sink>
**Severity rationale**: <one sentence, per severity.md>

**Vulnerable code**:
```<language>
<EXACT code from the stated file and lines>
```

**Remediation**:
1. <specific step>
2. <specific step>

**Secure implementation**:
```<language>
<complete working fix in the target language>
```
````

Optional lines, when relevant:
- `**Blast radius**: <factors>` for agent and model findings.
- `**Mitigations considered**: <what reduced severity>` from the false-positive filter.

## Field rules

- **Rule ID** comes from the module that produced the finding (for example `RG-XSS-001`).
- **Confidence**: `high` when the full source-to-sink path is confirmed in code; `medium` when one hop is inferred (dynamic dispatch, configuration not visible); `low` when the issue is a pattern match without a confirmed path. Low-confidence findings must say what would confirm them.
- **Trace** is required for injection, XSS, SSTI, deserialization, SSRF, prompt injection and tool-misuse findings. Use `n/a` for configuration findings such as hardcoded secrets.
- **Vulnerable code** must be copied from the stated location, must show the vulnerability, and must not be reused across findings.
- **Remediation** addresses the root cause; the implementation is production-ready, includes error handling, and matches the target language and framework.

## Pre-flight check (answer yes to all before presenting)

1. Is this the exact code from the exact `file:line` stated?
2. Does the snippet demonstrate the vulnerability in the title?
3. Is the snippet unique to this finding?
4. Would the remediation actually fix the problem?
5. Is the remediation in the target language?
6. Has the false-positive filter been applied?

If any answer is no: stop, re-examine the code, fix the finding, and re-run the check.
