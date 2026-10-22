---
id: RG-LOGIC
title: Business logic and authorization
auditor: access
discovery: Always runs.
rules:
  RG-LOGIC-001: Missing object-level authorization (IDOR)
  RG-LOGIC-002: Broken tenant isolation
  RG-LOGIC-003: Workflow or state-transition bypass
  RG-LOGIC-004: Race condition in a critical operation
  RG-LOGIC-005: Missing idempotency or replay protection
  RG-LOGIC-006: Unverified webhook, callback, or redirect
  RG-LOGIC-007: Trusting client-supplied business values (price, role, state)
---

# Business Logic and Authorization

## R: Risk First
**Goal**: Find flaws in intended behavior that input validation cannot catch.
**Risk**: Unauthorized access, privilege escalation, financial fraud, data manipulation, workflow bypass.
**Context**: Multi-step workflows, state machines, multi-tenant data, financial operations, integrations, and agent tools that act on objects.

## A: Attached Constraints
- ALWAYS enforce business rules on every code path and API endpoint.
- NEVER trust client-supplied business parameters or state (prices, roles, workflow step, owner IDs).
- ALWAYS validate state before each transition.
- NEVER allow workflow steps to be skipped or reordered without authorization.
- ALWAYS enforce object ownership and tenant isolation at the data access layer.
- ALWAYS make critical transactions atomic.
- ALWAYS verify webhooks and callbacks cryptographically.

## I: Isolation
- **Trust boundaries**: between tenants, between users of one tenant, between roles, and between the application and external systems (payment providers, identity providers, webhooks).
- **Untrusted inputs**: object IDs in paths and bodies, client-side state, external system responses, redirect URIs, and tool arguments chosen by an AI agent.
- **Least privilege**: scope every data query by the authenticated principal and tenant; agent tools act with the end user's permissions, never a global service role.

## L: Local Defaults

**When accessing objects**:
- Query by `(id, owner_id)` or `(id, tenant_id)` from the session, never by `id` alone; return 404 for objects the caller cannot see.

**When implementing workflows**:
- Use an explicit state machine; verify the current state server-side before each transition; use workflow tokens for multi-step processes.

**When handling money or scarce resources**:
- Use database transactions with the right isolation level or row locks; check availability at consumption time, not only at check time; use unique transaction IDs for idempotency.

**When integrating external systems**:
- Verify webhook signatures (HMAC with timestamp tolerance); validate redirect URIs against an exact allowlist; validate OAuth `state` and token audience.

**When an agent tool acts on objects**:
- Authorize each call against the end user's session; never let the model choose the principal.

## G: Generative Path Checks
1. Is every business process checked for bypass?
2. Is object-level authorization applied consistently on every endpoint and tool?
3. Are state transitions validated server-side?
4. Can multi-step processes be skipped or reordered?
5. Are race conditions handled with transactions or locks?
6. Are external integrations verified (signatures, redirect allowlists, audience)?
7. Are prices, discounts and totals computed server-side?
8. Are time-based operations and token expiry enforced?

## U: Uncertainty Disclosure
- **Safe default**: assume an endpoint needs object-level authorization unless the resource is public by design.
- **Escalate when**: authorization lives in a policy engine or service you cannot read; report with `medium` confidence.

## A: Auditability
- **Log**: authorization denials, state transitions on financial objects, webhook verification failures, cross-tenant access attempts.
- **Never log**: full payment details or secrets in transition payloads.

## R: Review
1. Did a new endpoint or tool take an object ID without an ownership check?
2. Did a new workflow step appear that can be called directly?
3. Could two concurrent requests both succeed where only one should?

**Core principle**: Logic flaws are about intent, not syntax. Enforce ownership, tenancy, sequence and atomicity on the server for every path, including paths an AI agent can drive.

## S: Spend
- Runs in: `railguards-auditor-access`.
- Gate: always.
- Scanners first: none reliable; use recon's route and model maps.
- Read: data-access functions and the handlers that call them with path or body IDs; transaction boundaries around payment and inventory code.
- Skip: read-only public catalog endpoints.
