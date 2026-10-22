# The RAILGUARDS Pillars

RAILGUARDS is the authoring template for every detection module in this framework. Each module answers the same nine questions, in the same order, so an agent (or a human reviewer) always knows where to find the risk, the hard rules, the trust boundaries, the safe defaults, the checks, the escalation path, the logging guidance, the review questions and the cost profile.

| Letter | Pillar | Question it answers |
|---|---|---|
| R | Risk First | What goal, risk and context does this module address? |
| A | Attached Constraints | What must ALWAYS or NEVER happen? |
| I | Isolation | Where are the trust boundaries, what is untrusted, and what privilege does each component get? |
| L | Local Defaults | What does the secure implementation look like, scenario by scenario? |
| G | Generative Path Checks | Which verifiable checks confirm the code is safe? |
| U | Uncertainty Disclosure | What is the safe default when requirements are unclear, and when should this escalate? |
| A | Auditability | What should be logged or documented so behavior can be reconstructed? |
| R | Review | Which questions keep this safe over time, and what is the core principle? |
| S | Spend | Who runs this module, what may they read, and how do they keep it cheap? |

## Pillar guidance

### R: Risk First
State the **Goal**, the **Risk** (what an attacker gains) and the **Context** (when the module applies). Keep it to three lines; the rest of the module expands on it.

### A: Attached Constraints
Absolute rules written as ALWAYS / NEVER statements. These are the lines a reviewer can check mechanically. Avoid soft language ("consider", "try to").

### I: Isolation
Modern security, especially agent security, is mostly about isolation. Name:
- the trust boundaries the data crosses (network, process, tenant, model context);
- which inputs are untrusted, including content an AI agent reads (files, web pages, tool output, retrieved documents);
- the least privilege each component, credential and tool should have;
- how failures are contained (sandboxing, separate accounts, separate models).

### L: Local Defaults
Concrete secure patterns the agent should reach for first, grouped by scenario ("When building database queries", "When an agent reads web content"). Include short code or configuration where it removes ambiguity. Match the target project's language when giving examples (see the audit orchestrator's language rules).

### G: Generative Path Checks
A numbered checklist of yes/no questions. Each question should be answerable by reading code or configuration.

### U: Uncertainty Disclosure
The secure default to choose when requirements are unclear, how to state confidence in a finding, and the conditions under which the agent should stop and ask a human or recommend specialist review.

### A: Auditability
Security events worth logging, what must never be logged (secrets, full prompts with user data, tokens), and code comments worth requiring at sensitive sites.

### R: Review
Questions for ongoing review (after refactors, new endpoints, new tools) followed by a one-paragraph **Core principle**.

### S: Spend
How the module stays cheap:
- which subagent runs it and on which model tier;
- which discovery check gates it (skip the module entirely if the check is negative);
- which scanners to run first, so the model triages results instead of reading every file;
- what to read (exact sinks and their callers, line ranges) and what never to read;
- the output shape (compact findings, no raw file dumps).

## Module template

Copy this skeleton when adding a module to `skills/railguards-audit/modules/`.

```markdown
---
id: RG-XXX
title: <Module title>
auditor: <web | access | secrets | ai>
discovery: <one-line check that gates this module>
---

# <Module title>

## R: Risk First
**Goal**: ...
**Risk**: ...
**Context**: ...

## A: Attached Constraints
- ALWAYS ...
- NEVER ...

## I: Isolation
- Trust boundaries: ...
- Untrusted inputs: ...
- Least privilege: ...

## L: Local Defaults
**When <scenario>**:
- ...

## G: Generative Path Checks
1. ...

## U: Uncertainty Disclosure
- Safe default: ...
- Escalate when: ...

## A: Auditability
- Log: ...
- Never log: ...

## R: Review
1. ...

**Core principle**: ...

## S: Spend
- Runs in: `railguards-auditor-<x>`
- Gate: ...
- Scanners first: ...
- Read: ...
- Skip: ...
```

## Authoring rules

1. Keep modules focused: one vulnerability family per module.
2. Every finding a module can produce needs a stable rule ID (`RG-<FAMILY>-NNN`) so evals and exports can track it.
3. Prefer architectural remediation over pattern blocklists.
4. Never weaken a v1 detection rule without recording why in `MIGRATION.md`.
5. CI rejects detection modules that are missing any of the nine pillar headings.
