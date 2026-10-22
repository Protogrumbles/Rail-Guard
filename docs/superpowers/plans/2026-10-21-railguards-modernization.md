# RAILGUARDS Modernization Implementation Plan

> **For agentic workers:** Execute task-by-task (inline execution chosen). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the RAILGUARD v1 rule set with the RAILGUARDS two-layer framework described in `docs/superpowers/specs/2026-10-21-railguards-modernization-design.md`.

**Architecture:** A portable core (`AGENTS.md`, Agent Skills under `skills/`) plus a single standard-library Python hook engine and helper scripts, with thin per-tool adapters (`adapters/cursor`, `adapters/claude-code`) copied into target projects by `scripts/install.sh`.

**Tech Stack:** Markdown (skills, modules, subagents), Python 3.9+ standard library (hooks, scripts, tests), POSIX shell (installer), GitHub Actions (CI).

## Global Constraints

- Always-on layer (`AGENTS.md` body between markers): at most 60 lines and at most 1,200 estimated tokens (chars / 4).
- Python code uses only the standard library; `tiktoken` is optional and detected at runtime.
- Hook profiles: `ask` (default) and `strict`; config from `RAILGUARDS_PROFILE` env var, then `.railguards/config.json`.
- Every detection module contains the nine headings: `## R: Risk First`, `## A: Attached Constraints`, `## I: Isolation`, `## L: Local Defaults`, `## G: Generative Path Checks`, `## U: Uncertainty Disclosure`, `## A: Auditability`, `## R: Review`, `## S: Spend`.
- Installer never overwrites user content: marker blocks for Markdown, merges for JSON.
- Results go to chat first; files only on user request.

---

## File map

| Path | Responsibility |
|---|---|
| `AGENTS.md` | Always-on guardrails (security, spend, triggers) inside RAILGUARDS markers |
| `core/pillars.md` | Pillar definitions and module template |
| `skills/railguards-audit/SKILL.md` | Audit orchestrator |
| `skills/railguards-audit/modules/*.md` | 15 modules (see spec 6.3) |
| `skills/railguards-token-plan/SKILL.md` + `references/*.md` | Token workflow, layer catalog, templates |
| `skills/railguards-vet/SKILL.md` | Vetting workflow |
| `hooks/guard.py` | Hook engine: `decide_shell`, `decide_read`, `scan_edit`, `log_mcp`; CLI `--tool {cursor,claude} --event {shell,read,edit,mcp}` |
| `scripts/check_unicode.py` | `scan_text(text) -> list[Finding]`, CLI over paths, exit 1 on findings |
| `scripts/measure_overhead.py` | `measure(root) -> dict`; `--save-baseline`, `--compare`, `--json` |
| `scripts/mcp_lock.py` | `snapshot`, `verify`; `--config`, `--tools-file`, `--probe` |
| `scripts/install.sh` + `scripts/install_helpers.py` | Tool detection, copy, marker-block and JSON merge |
| `scripts/ci_checks.py` | Budget, unicode, pillars, mirror sync |
| `adapters/cursor/*` | `rules/railguards.mdc`, `agents/*.md`, `hooks.json` |
| `adapters/claude-code/*` | `CLAUDE.md`, `agents/*.md`, `settings.json` |
| `evals/*` | Four fixtures with `expected.json`, `score.py`, guardrail scenarios |
| `tests/test_*.py` | Unit tests |
| `.github/workflows/ci.yml` | CI |
| `README.md`, `MIGRATION.md` | Docs |

## Interfaces shared across tasks

- `hooks/guard.py` imports `scripts/check_unicode.py` via path insertion relative to its own location, with an installed-layout fallback (`.railguards/scripts/`).
- `check_unicode.scan_text(text: str) -> list[dict]` where each dict has `line`, `col`, `codepoint` (e.g. `"U+202E"`), `name`.
- `measure_overhead.measure(root: Path) -> dict` with keys `always_on` (list of `{path, lines, tokens}`), `mcp_servers` (list of `{name, source, tool_tokens}`), `total_tokens`.
- `mcp_lock.snapshot(config_paths, tools_by_server) -> dict` and `mcp_lock.verify(lock, config_paths, tools_by_server) -> list[str]` (drift messages).
- Audit JSON export schema (consumed by `evals/score.py`): `{"findings": [{"rule_id", "title", "severity", "confidence", "file", "line_start", "line_end"}]}`.

## Tasks

### Task 1: Foundation
- [ ] Tag `81ddc65` as `v1-legacy` and push the tag.
- [ ] Write `core/pillars.md` (nine pillars, module template, authoring rules).
- [ ] Write `AGENTS.md` with the three blocks inside `<!-- RAILGUARDS:BEGIN -->`/`<!-- RAILGUARDS:END -->`.
- [ ] Verify: `awk '/RAILGUARDS:BEGIN/{f=1;next}/RAILGUARDS:END/{f=0}f' AGENTS.md | wc -l` prints 60 or less.
- [ ] Commit.

### Task 2: Audit skill
- [ ] Write `skills/railguards-audit/SKILL.md` (scope selection, pipeline, sequential fallback, exclusions, language matching, report template, export).
- [ ] Migrate the eleven v1-derived modules to the nine-pillar template, keeping every v1 indicator list, severity table and decision tree.
- [ ] Write `llm-app-security.md`, `mcp-and-tools.md`, `agent-supply-chain.md`.
- [ ] Verify pillar headings: `python3 scripts/ci_checks.py --only pillars` (after Task 6 creates it; until then grep for the nine headings).
- [ ] Commit.

### Task 3: Token-plan skill
- [ ] Write a failing test `tests/test_measure_overhead.py` (fixture repo with `AGENTS.md`, an `alwaysApply` rule, a non-always rule, `.cursor/mcp.json`; asserts counted files, excluded files, server count, baseline compare delta).
- [ ] Implement `scripts/measure_overhead.py` until tests pass.
- [ ] Write `SKILL.md` and references (`layers.md`, `subagents.md`, `code-graph.md`, `memory.md`, `ignore-files.md`, `templates/`).
- [ ] Commit.

### Task 4: Vet skill and MCP lock
- [ ] Write failing tests `tests/test_check_unicode.py` and `tests/test_mcp_lock.py`.
- [ ] Implement `scripts/check_unicode.py` and `scripts/mcp_lock.py` until tests pass.
- [ ] Write `skills/railguards-vet/SKILL.md`.
- [ ] Commit.

### Task 5: Hooks, adapters and installer
- [ ] Write failing tests `tests/test_guard.py` (shell, read, edit, mcp decisions for both profiles and both output formats) and `tests/test_install.py` (marker block insert/replace, JSON hook merge idempotency, end-to-end install into temp dirs for `cursor`, `claude`, `both`).
- [ ] Implement `hooks/guard.py`, `scripts/install_helpers.py`, `scripts/install.sh`.
- [ ] Write adapter files: Cursor rule mirror, six subagents per tool, `hooks.json`, `settings.json`, `CLAUDE.md`.
- [ ] Commit.

### Task 6: Evals and CI
- [ ] Create four fixtures under `evals/fixtures/` with `expected.json`.
- [ ] Write a failing test `tests/test_score.py`; implement `evals/score.py`.
- [ ] Write `evals/guardrails/scenarios.md`.
- [ ] Implement `scripts/ci_checks.py` (budget, unicode, pillars, mirrors); add `.github/workflows/ci.yml`.
- [ ] Run `python3 -m unittest discover -s tests -v` and `python3 scripts/ci_checks.py`; both must pass.
- [ ] Commit.

### Task 7: Docs and removal of v1 rules
- [ ] Write `MIGRATION.md`; rewrite `README.md`.
- [ ] `git rm -r rules/`.
- [ ] Re-run all checks; commit; push; update the PR.
