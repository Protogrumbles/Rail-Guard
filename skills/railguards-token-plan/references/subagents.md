# Subagents for token efficiency

Subagents run in their own context and return a summary, so the main conversation stays small. They cost a startup overhead each, so use them for broad or repetitive work, not one-file lookups.

## Recommended set

| Subagent | When to add | Model tier | Returns |
|---|---|---|---|
| `recon` | Any medium or large repo | Cheaper/faster | Where things are and how they connect, under about 20 lines with file:line pointers |
| `test-runner` | Noisy test suites | Cheaper/faster | Only failing tests, assertion messages, file:line |
| `<package>-explorer` | Monorepos with independent packages | Cheaper/faster | Package-scoped answers |
| `docs-lookup` | Frequent framework or API questions | Cheaper/faster | Short answer with links |
| `reviewer` | Before commits on risky changes | Same as parent | Findings only |

## File formats

Cursor reads `.cursor/agents/*.md` (and also `.claude/agents/`, with `.cursor/` taking precedence). Claude Code reads `.claude/agents/*.md`.

**Cursor frontmatter**: `name`, `description`, `model` (`inherit` or a model ID; append options like `[effort=low]` where supported), `readonly` (true for search-only agents), `is_background`.

**Claude Code frontmatter**: `name`, `description`, `tools` (comma-separated allowlist, for example `Read, Grep, Glob, Bash`), `model` (`haiku`, `sonnet`, `opus` or `inherit`).

Templates: `templates/subagent-recon.cursor.md`, `templates/subagent-recon.claude.md`, `templates/subagent-test-runner.cursor.md`, `templates/subagent-test-runner.claude.md`.

## Writing good subagent prompts

- Put the trigger words in `description` ("Use for broad codebase searches", "Use to run tests").
- State the output budget ("Answer in at most 20 lines").
- Forbid raw dumps ("Never paste whole files; cite file:line").
- Keep search agents read-only.
- Name the cheaper model explicitly when the tool supports it.
