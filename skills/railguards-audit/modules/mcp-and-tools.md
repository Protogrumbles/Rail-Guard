---
id: RG-MCP
title: MCP servers, clients, and agent tools
auditor: ai
discovery: MCP SDKs, MCP server or client code, agent tool definitions, or agent-to-agent protocols are present.
rules:
  RG-MCP-001: Tool poisoning (instructions or hidden text in tool names, descriptions, or schemas) [ASI04]
  RG-MCP-002: Tool definitions can change after approval without detection (rug pull) [ASI04]
  RG-MCP-003: Cross-server tool shadowing or name collision [ASI04]
  RG-MCP-004: Confused deputy or token passthrough [ASI03]
  RG-MCP-005: Missing or weak authorization on remote MCP server (OAuth scope, audience, or resource validation) [ASI03]
  RG-MCP-006: Insecure session handling (predictable IDs, session used as authentication) [ASI03]
  RG-MCP-007: Local server exposure (bound to 0.0.0.0, no Origin check, DNS rebinding) [ASI02]
  RG-MCP-008: Command injection or path traversal in a tool implementation [ASI05]
  RG-MCP-009: Over-broad tool capability (unrestricted filesystem, shell, network, or database access) [ASI02]
  RG-MCP-010: Insecure inter-agent communication (unauthenticated or unvalidated agent messages) [ASI07]
---

# MCP Servers, Clients, and Agent Tools

## R: Risk First
**Goal**: Ensure tools exposed to agents cannot be poisoned, hijacked or abused beyond their intended scope.
**Risk**: Data exfiltration and destructive actions through legitimate tools, credential theft, remote code execution on developer machines or servers, impersonation between agents.
**Context**: Code that implements MCP servers, consumes MCP servers as a client or host, defines agent tools in any framework, or exchanges messages between agents (A2A and similar). Maps to OWASP Agentic ASI02, ASI03, ASI04, ASI05 and ASI07.

## A: Attached Constraints
- NEVER place instructions to the model in tool descriptions beyond describing what the tool does; NEVER include hidden Unicode or markup in tool metadata.
- ALWAYS pin and record tool definitions after approval and detect changes before use.
- NEVER pass a user's or client's token through to downstream APIs; a server must only accept tokens issued for itself (audience-bound) and obtain its own tokens for downstream calls.
- ALWAYS authorize every tool call; NEVER use the MCP session ID as authentication.
- ALWAYS bind local HTTP servers to `127.0.0.1`, validate the `Origin` header, and require authentication.
- NEVER build shell commands, SQL or file paths from tool arguments without the controls in `input-validation.md` and `sqli.md`.
- ALWAYS scope filesystem, network and database access per tool to the minimum needed.
- ALWAYS authenticate and validate messages between agents.

## I: Isolation
- **Trust boundaries**: host ↔ MCP server (each server is a separate trust domain); MCP server ↔ downstream APIs; client ↔ remote server over the network; agent ↔ agent.
- **Untrusted inputs**: tool names, descriptions and schemas from third-party servers; tool results; tool arguments chosen by the model (which may be attacker-steered); messages from other agents.
- **Least privilege**:
  - One server per capability; avoid "do anything" servers (raw shell, unrestricted SQL).
  - Read-only by default; separate write tools that require approval.
  - Run local servers as an unprivileged user or in a container with explicit mounts and egress allowlists.
  - Request the narrowest OAuth scopes; keep tokens short-lived.

## L: Local Defaults

**When implementing an MCP server**:
- Validate every argument against the declared JSON schema and business rules; use argument arrays for subprocesses; canonicalize and confine paths to an allowed root.
- Keep descriptions factual: what the tool does, its inputs, its side effects. No "always call this first", no instructions about other tools, no hidden text.
- For HTTP transport: bind to `127.0.0.1` for local use, check `Origin`, require auth, use cryptographically random session IDs bound to the authenticated user, and never treat a session as proof of identity.
- For remote servers: implement OAuth 2.1 as in the MCP authorization spec, validate token audience and resource indicators, and never forward client tokens downstream.

**When building an MCP client or host**:
- Show users the full tool description and require approval on first use and on any change; hash tool definitions and re-verify on each session (`scripts/mcp_lock.py`).
- Namespace tools by server and refuse duplicate names across servers.
- Treat tool results as untrusted content (see `llm-app-security.md`).

**When defining tools in an agent framework**:
- Declare side effects; mark destructive tools as requiring confirmation; enforce authorization inside the tool using the end user's identity.

**When agents talk to agents**:
- Authenticate peers (mTLS or signed messages), validate message schemas, include nonces or timestamps against replay, and never let one agent's output grant another agent new permissions.

## G: Generative Path Checks
1. Do any tool names, descriptions or schemas contain instructions, references to other tools, or hidden Unicode?
2. Are tool definitions pinned or hashed, and are changes detected before use?
3. Are tool names namespaced and collisions rejected?
4. Does the server accept only tokens issued for itself and obtain separate tokens downstream?
5. Is every tool call authorized for the calling user, independent of session ID?
6. Are local HTTP servers bound to loopback with `Origin` checks and authentication?
7. Are tool arguments validated before reaching shells, SQL, files or URLs?
8. Is each tool's filesystem, network and database access limited to its purpose?
9. Are inter-agent messages authenticated, schema-validated and replay-protected?

## U: Uncertainty Disclosure
- **Safe default**: treat every third-party server as untrusted until vetted with `railguards-vet`; treat every tool argument as attacker-controlled.
- **Escalate when**: a server exposes shell, unrestricted filesystem or database access to a model that also reads untrusted content; or a remote server forwards client tokens.

## A: Auditability
- **Log**: tool invocations (server, tool, user, argument hash, result size, duration), approvals, definition changes detected, auth failures.
- **Never log**: tokens, full arguments containing secrets, raw tool results with PII.

## R: Review
1. Did a server update change any tool description or schema?
2. Did a new server introduce a tool name that already exists?
3. Did a tool gain write, network or shell capability?
4. Are OAuth scopes and token audiences still minimal?

**Core principle**: Every tool is an attack surface and every tool description is untrusted text. Pin what you approved, authorize every call as the real user, confine each tool to its purpose, and never let a token or a message cross a trust boundary unchecked.

## S: Spend
- Runs in: `railguards-auditor-ai`.
- Gate: recon's MCP/tools discovery check is positive.
- Scanners first: `scripts/check_unicode.py` on tool metadata files; Semgrep for command injection in tool handlers.
- Read: tool registration code (names, descriptions, schemas), each tool handler's sink lines, auth middleware, transport setup (bind address, Origin checks).
- Skip: SDK internals.
