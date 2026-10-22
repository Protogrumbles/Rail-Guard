---
name: railguards-security-audit
description: Run a RAILGUARDS security audit of changed files only (uncommitted changes plus commits not on the default branch). Use when the user invokes /railguards-security-audit.
disable-model-invocation: true
---

# Security audit (changed files)

Find `railguards-audit/SKILL.md` in `.agents/skills/`, `.claude/skills/`, or `.cursor/skills/` and follow it from start to finish.

The scope is already chosen: **changed files**, as that skill's scope table defines it. Do not ask which scope. Run that skill's changed-files git command, then the rest of the pipeline.

If no `railguards-audit` skill or `.railguards/` directory exists, say RAILGUARDS is not installed and stop. Do not invent findings.
