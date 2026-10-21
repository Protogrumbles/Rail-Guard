# Session memory

New sessions start with empty context. Without written memory, agents re-explore the same architecture every time.

## Options, simplest first

1. **`docs/ARCHITECTURE.md`** (template: `templates/ARCHITECTURE.md`)
   One page: modules and responsibilities, data flow, conventions, where to find things. Reference it from `AGENTS.md` with one line so agents read it only when needed: `For architecture, read docs/ARCHITECTURE.md before exploring.`

2. **`.railguards/progress.md`** (template: `templates/progress.md`)
   A running note for multi-session tasks: goal, done, next, open questions, key files. Agents update it at the end of a session. Add `.railguards/progress.md` to `.gitignore` if it is personal.

3. **Obsidian vault or Markdown notes directory**
   For teams that want linked decision records (ADRs), meeting notes and research next to code. Options:
   - Keep the vault inside the repo (`docs/vault/`) so agents read it with normal file tools; no extra server needed.
   - Or connect an existing vault through an Obsidian MCP server.

   Vetting requirements for an Obsidian MCP server (run `railguards-vet`):
   - runs locally and only accesses the vault directory;
   - pinned to an exact version from the official publisher;
   - read-only unless the user wants the agent to write notes;
   - any API key for the Obsidian Local REST API plugin stays in environment variables, not in `mcp.json`.

## What to avoid

- Long memory files loaded on every turn (that moves cost into layer 1).
- Memory written from untrusted content (web pages, issues) without review; that is a memory-poisoning path.
