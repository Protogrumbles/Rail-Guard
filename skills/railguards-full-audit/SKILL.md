---
name: railguards-full-audit
description: Run a RAILGUARDS full security audit of the whole repository. Use when the user invokes /railguards-full-audit.
disable-model-invocation: true
---

# Full security audit (whole repository)

Find `railguards-audit/SKILL.md` in `.agents/skills/`, `.claude/skills/`, or `.cursor/skills/` and follow it from start to finish.

The scope is already chosen: **whole repository**. Do not ask which scope. Skip the changed-files git command and audit the repo, still applying that skill's exclusions.

If no `railguards-audit` skill or `.railguards/` directory exists, say RAILGUARDS is not installed and stop. Do not invent findings.
