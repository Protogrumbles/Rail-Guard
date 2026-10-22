---
name: railguards-token-plan
description: Diagnose where an AI coding agent wastes tokens in this repository and produce a layer-by-layer plan (fixed context overhead, code reading, command output, session memory, exploration with subagents, code structure), then scaffold the chosen changes and measure the before/after fixed overhead. Use when the user asks for a "token plan", to reduce token usage, cut agent cost, set up subagents, a code graph (for example Graphify or Serena), or a memory vault (for example Obsidian).
---

# RAILGUARDS Token Plan

Goal: spend fewer tokens for the same quality of work, with evidence. Token savings depend on the repository and the questions asked, so recommend by **layer**, state honest ranges, and measure what can be measured exactly.

References in `references/` next to this file:
- `layers.md`: the layer catalog with criteria, expected effects and trade-offs
- `subagents.md`: which subagents to create and how
- `code-graph.md`: code graph and symbol tools, with benchmark evidence
- `memory.md`: progress notes, architecture docs, Obsidian vaults
- `ignore-files.md`: ignore and deny configuration per tool
- `templates/`: files to scaffold

Load a reference only when the plan needs it.

## Step 1: Diagnose (cheap commands only, do not read source files)

Run these and keep only the summary:

```bash
python3 <railguards>/scripts/measure_overhead.py . --save-baseline     # fixed overhead per turn
git ls-files | wc -l                                                   # tracked files
git ls-files | sed -n 's/.*\.\([A-Za-z0-9]*\)$/\1/p' | sort | uniq -c | sort -rn | head -8   # languages
git ls-files -z | xargs -0 wc -l 2>/dev/null | sort -rn | sed -n '2,11p'   # largest files
ls -d */ 2>/dev/null | head -30                                        # top-level layout
ls .cursorignore .cursorindexingignore .gitignore .claude/settings.json 2>/dev/null
ls pnpm-workspace.yaml lerna.json nx.json turbo.json go.work Cargo.toml 2>/dev/null   # monorepo markers
```

`<railguards>` is the installed scripts directory (`.railguards/scripts` in a project that ran the installer).

Also note:
- test and build commands (from `package.json`, `Makefile`, `pyproject.toml`) and whether they have quiet or failures-only modes;
- generated, vendored or very large directories that are tracked (`dist/`, `vendor/`, fixtures, snapshots, data files);
- configured MCP servers and whether each is actually used for this project.

Classify the repository:
- **Small**: under about 300 tracked source files, single package.
- **Medium**: about 300 to 3,000 files, or several packages.
- **Large**: over about 3,000 files, or a monorepo with many packages or services.

## Step 2: Write the token plan

Present it in chat using this structure. Include only recommendations that apply to this repository.

```markdown
# Token plan for <repo>

**Profile:** <small|medium|large>, <languages>, <N> files, monorepo: <yes|no>
**Fixed overhead now:** <N> tokens per turn (Cursor) / <N> (Claude Code); MCP servers: <N> (<names>)

## Recommendations by layer
### 1. Fixed context overhead
- <recommendation> — why: <evidence from diagnosis> — effect: <exact tokens saved, from measure_overhead> — trade-off: <...>
### 2. Reading code
### 3. Command output
### 4. Session memory
### 5. Exploration (subagents)
### 6. Code structure

## What I can set up now
- [ ] <file or config to create> (<layer>)
...

Effects for layer 1 are measured; all other effects are estimates from published benchmarks and vary by workload.
```

Rules for recommendations (details in `references/layers.md`):
1. **One tool per layer.** Tools in the same layer overlap; tools in different layers stack.
2. **Cheapest fix first.** Ignore files and trimming always-on context come before installing anything.
3. **Match tier to size.** Do not recommend a code graph for a small repo; the indexing and query overhead can exceed the savings.
4. **Every third-party tool needs vetting.** Mark each with "requires railguards-vet" and run the vet before scaffolding it.
5. **Be honest about evidence.** Quote ranges and their source; say when results are mixed.

## Step 3: Scaffold (only after the user confirms which items)

For each confirmed item:
1. If it adds a third-party tool, MCP server, plugin or package, run the `railguards-vet` skill first and stop if the verdict is Reject.
2. Create or update files from `references/templates/`, adapting names, paths and commands to this repository. Never overwrite user content: append to ignore files, merge JSON, and use marker blocks in Markdown.
3. For install commands of third-party tools, print the exact pinned command and let the user run it (or run it only with explicit approval).

Typical scaffolds:
- `.cursorignore` / Claude `permissions.deny` entries for generated, vendored and data paths
- Subagents in `.cursor/agents/` and `.claude/agents/` (recon on a cheaper model, test runner that returns only failures, per-package explorers in monorepos, docs lookup)
- Nested `AGENTS.md` per package in monorepos, moving package-specific instructions out of the root file
- Conversion of large always-on rules into skills or description-triggered rules
- `docs/ARCHITECTURE.md` and `.railguards/progress.md` templates
- MCP config for a vetted code graph, symbol tool or memory server, pinned to an exact version

## Step 4: Measure

After scaffolding:

```bash
python3 <railguards>/scripts/measure_overhead.py . --compare
```

Report the exact before/after for fixed overhead per tool. For MCP servers whose tool-definition size is unknown, offer to record it with `scripts/mcp_lock.py snapshot --probe` (this starts the configured stdio servers to list their tools; ask first).

For other layers, suggest a lightweight check the user can do: repeat a typical task in a fresh session and compare the usage shown by their tool.

## Spend discipline for this skill

- Diagnosis uses shell summaries only; do not open source files.
- Load at most the references the plan needs.
- Keep the plan under about 60 lines; details go into the scaffolded files.
