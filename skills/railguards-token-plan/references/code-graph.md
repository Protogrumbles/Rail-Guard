# Code graph and symbol tools

## What they do

- **Symbol tools** (for example Serena) expose language-server features to the agent: find a symbol's definition, references, and outline without reading whole files.
- **Code graphs** (for example Graphify, CodeGraph) parse the repository (usually with tree-sitter) into a graph of files, symbols, imports and calls that the agent queries instead of grepping.
- **Code search platforms** (for example Sourcegraph through its MCP server) serve organizations that already index many repositories.

## Evidence (October 2026)

| Source | Setup | Result |
|---|---|---|
| [token-consumption-benchmark](https://github.com/vagkaratzas/token-consumption-benchmark) | Claude Code, 8 comprehension tasks, ~30-file Python app | Serena −66%, Graphify −66%, CodeGraph −54% tokens vs no tool; stacking a code-read tool with command and prose compression reached about −70% |
| [Graphify vs. grep](https://constantinsblog.eu/posts/graphify-llm-query-tool/) | 11 questions, capable baseline agent using `rg` and targeted reads | Graphify inspected 15% fewer files but used about 50% more total input and cost about 10% more |
| Graphify project docs | Full corpus vs scoped subquery | Up to 71.5x reduction on one community workload; about 1x on a small synthetic library |

**Reading the evidence**: graph compression is real, but end-to-end savings depend on the baseline. Against an agent that already searches well, a graph mainly helps with call-path tracing and orientation in large codebases. Measure on your own tasks before standardizing.

## When to recommend

- **Small repo**: do not; habits and ignore files are enough.
- **Medium repo**: a symbol tool first.
- **Large repo or monorepo**: a code graph for orientation, optionally alongside a symbol tool for precise lookups (they overlap partially; pick one primary).

## Usage pattern to put in `AGENTS.md` (one line)

`Use the code graph to find candidate symbols and call paths, then confirm in source before editing or reporting.`

## Vetting notes

Run `railguards-vet` before installing. Check in particular:
- whether parsing is fully local (tree-sitter) and which passes send content to a model or API (some tools run an LLM pass over docs, PDFs or images);
- what directories the tool indexes and where it stores the index (add the index directory to `.gitignore` if it should not be committed);
- that the installed package name is exactly the official one and pinned to a version;
- whether the MCP server exposes write or shell capabilities (it should not need them).
