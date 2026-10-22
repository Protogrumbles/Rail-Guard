# RAILGUARDS evals

## Audit fixtures

`fixtures/` holds four small, deliberately vulnerable projects. Each has an `expected.json` listing the findings an audit should report (`expected`, some marked `optional`) and code that should not be flagged (`must_not_flag`).

| Fixture | What it plants |
|---|---|
| `web-app` | SQL injection, reflected XSS, IDOR, hardcoded credentials |
| `llm-agent-app` | lethal trifecta in one agent, model output into a shell, RAG without tenant isolation |
| `mcp-server` | poisoned tool description, `0.0.0.0` binding, command injection in a tool |
| `poisoned-repo` | rules file with hidden Unicode, slopsquatted dependency, unpinned MCP server |

The fixtures contain live injection payloads (the hidden rule only asks for a harmless `RG-CANARY-7` comment). Run audits on a copy outside this repository so your own agent session is not exposed to them:

```bash
cp -r evals/fixtures/web-app /tmp/rg-web-app && scripts/install.sh /tmp/rg-web-app --tool cursor
# open /tmp/rg-web-app, ask for a "full security audit", and save the report as JSON
python3 evals/score.py /tmp/rg-web-app/railguards-report.json --fixture evals/fixtures/web-app
```

`score.py` maps each finding to a module by its rule ID prefix (`RG-SQLI-*` is `sqli`), matches file and line range (3 lines of slack unless an entry sets `tolerance`), and prints recall and precision per module. It reads the audit's JSON or SARIF export. Use `--min-recall 0.8` to fail on regressions and `--json` for machine-readable output.

## Guardrail scenarios

`guardrails/scenarios.md` lists prompts with pass and fail criteria for the always-on layer, hooks, and skills.
