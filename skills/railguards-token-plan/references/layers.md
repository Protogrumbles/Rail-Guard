# Token layers catalog

Each agent turn pays for tokens in a few distinct layers. Tools and habits target one layer each, so the plan works layer by layer.

| Layer | What costs tokens | Measurable exactly? |
|---|---|---|
| 1. Fixed context overhead | Always-on rules, `AGENTS.md`/`CLAUDE.md`, skill and rule descriptions, MCP tool definitions, paid on every turn | Yes (`measure_overhead.py`) |
| 2. Reading code | Grep results and file reads the agent pulls in to understand code | Estimate |
| 3. Command output | Test, build, lint and log output returned to the agent | Estimate |
| 4. Session memory | Re-discovering architecture and decisions in each new session | Estimate |
| 5. Exploration | Broad searches and reads that fill the main context | Estimate |
| 6. Code structure | Very large files that force large reads for small changes | Estimate |

## 1. Fixed context overhead

**Signals**: `measure_overhead.py` shows more than about 2,000 tokens per turn; many `alwaysApply: true` rules; long root `AGENTS.md`; MCP servers configured but unused for this project; duplicate instructions across `AGENTS.md`, `CLAUDE.md` and rules.

**Recommendations**:
- Convert long always-on rules into skills (`SKILL.md`) or description-triggered rules; keep only rules every task needs.
- Remove or disable MCP servers this project does not use. Each server's tool definitions are sent on every turn; large servers can cost thousands of tokens.
- De-duplicate: make `CLAUDE.md` import `AGENTS.md` (`@AGENTS.md`) instead of copying it.
- In monorepos, move package-specific guidance into nested `AGENTS.md` files that load only when working in that package.

**Effect**: exact, from `measure_overhead.py --compare`.
**Trade-off**: on-demand content depends on good descriptions; write descriptions with the trigger words users actually say.

## 2. Reading code

**Signals**: medium or large repo; agents grep broadly and open many files; call-path questions ("who calls X?") are common.

**Recommendations by tier**:
- **Small**: ignore files plus the always-on search habits are enough.
- **Medium**: a symbol-level tool (LSP-backed, for example Serena) so the agent can fetch a symbol's definition and references instead of whole files.
- **Large or monorepo**: a code graph (for example Graphify, CodeGraph, or Sourcegraph MCP for organizations already on Sourcegraph) for orientation and call-path tracing.

Always follow **graph for orientation, source for evidence**: use the graph to find candidate symbols and paths, then confirm in the source before editing or reporting.

**Effect**: published benchmarks range from about 54 to 66 percent fewer tokens on comprehension tasks in a small Python app, but an independent end-to-end test found a code graph increased total input by about 50 percent compared with a capable agent using grep and targeted reads. See `code-graph.md`.
**Trade-off**: indexing time, index freshness, and query overhead; semantic passes over docs may send content to a model provider.

## 3. Command output

**Signals**: test suites or builds print thousands of lines; agents re-run noisy commands.

**Recommendations**:
- Use quiet or failures-only flags (`pytest -q --no-header -rf`, `jest --silent`, `go test ./... 2>&1 | grep -E 'FAIL|panic'`, `cargo test -q`, `npm run build --silent`).
- Add a test-runner subagent that runs the suite and returns only failing test names, assertion messages and file:line.
- Optional: an output-compression tool (for example rtk) or a structured-output MCP server (for example Pare). Pick one.

**Effect**: benchmark results show about 36 percent fewer tokens on command-heavy tasks for output compression and up to about 72 percent for structured test output, with little effect on non-command tasks.
**Trade-off**: compressed output can hide context needed for unusual failures; keep a way to get the full log.

## 4. Session memory

**Signals**: long-lived project; every new session re-explores the same architecture; decisions are scattered in chats.

**Recommendations (simplest first)**:
1. `docs/ARCHITECTURE.md`: one page on modules, data flow and conventions; referenced from `AGENTS.md`.
2. `.railguards/progress.md`: a short running note for multi-session tasks (goal, done, next, open questions).
3. An Obsidian vault (or any Markdown notes directory) for teams that want linked decision records, accessed through a vetted MCP server limited to the vault directory.

**Effect**: estimate; avoids repeated exploration at the start of sessions.
**Trade-off**: notes go stale; keep them short and update them as part of finishing a task.

## 5. Exploration (subagents)

**Signals**: tasks touch many areas; the main context fills with search results; monorepo packages are independent.

**Recommendations**:
- A read-only recon subagent on a cheaper model that answers "where is X and how does it work" in under about 20 lines.
- A test-runner subagent (see layer 3).
- One explorer per package or service in monorepos.
- A docs-lookup subagent for framework documentation questions.
- Run independent subagents in parallel.

**Effect**: estimate; the main context receives summaries instead of raw reads, and cheaper models handle search.
**Trade-off**: each subagent has its own startup overhead; do not delegate tasks that need only one or two reads.

## 6. Code structure

**Signals**: files over about 1,000 lines that are edited often; generated files tracked in source directories.

**Recommendations**:
- Split large, frequently edited files along clear responsibility boundaries.
- Move generated code to clearly named directories and ignore them for agents.

**Effect**: estimate; smaller files mean smaller reads per change.
**Trade-off**: refactoring cost and churn; only split files the team edits often.
