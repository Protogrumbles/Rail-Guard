---
name: railguards-status
description: Check that RAILGUARDS is installed in this project and report what is active, then stop. Use only for /railguards-status or when the user asks whether RAILGUARDS is installed or loaded before work starts.
disable-model-invocation: true
---

# RAILGUARDS status

Confirm the install, then stop. Do not audit, vet, edit, scaffold, or start the user's task. Do not change files.

Run these checks from the project root.

1. **Always-on text.** `AGENTS.md` contains `<!-- RAILGUARDS:BEGIN -->`, or `.cursor/rules/railguards.mdc` exists.
2. **Skills.** Under `.agents/skills/`, `.claude/skills/`, or `.cursor/skills/`, look for `railguards-audit`, `railguards-token-plan`, `railguards-vet`, `railguards-status`, `railguards-security-audit`, `railguards-full-audit`, and `railguards-mcp-vet`.
3. **Subagents.** Count `railguards-*.md` in `.cursor/agents/` and `.claude/agents/`.
4. **Hooks.** `.cursor/hooks.json` or `.claude/settings.json` contains `.railguards/hooks/guard.py`.
5. **Engine.** `.railguards/hooks/guard.py`, `.railguards/scripts/measure_overhead.py`, and `.railguards/config.json` exist. Read `profile` from the config.
6. **Leftover v1 rules.** In `.cursor/rules/`, any `*-railguard*.mdc`, `exclusions.mdc`, or the numbered v1 files such as `00-railguard-core.mdc`.

Then run:

```bash
printf '%s' '{"command":"ls","workspace_roots":["."]}' | python3 .railguards/hooks/guard.py --tool cursor --event shell
python3 .railguards/scripts/measure_overhead.py --json
```

The hook command is healthy only when it prints a JSON object with `"permission": "allow"`.

Reply with only this report:

```
RAILGUARDS status: ready | incomplete
- Always-on: yes/no (<file>)
- Skills: <n>/7 (<missing names, or "none missing">)
- Subagents: <n>
- Hooks configured: yes/no (<file>)
- Hook engine runs: yes/no
- Profile: ask | strict | missing
- Fixed overhead: <tokens per tool>
- v1 rules still installed: none | <file names>
```

State two limits plainly: choosing `/railguards-status` from the menu shows this chat can see the skills; the hook engine check shows the script runs. Cursor attaches hooks when the chat starts, so a chat opened before install will not enforce them until a new chat.

If the status is incomplete, tell the user to re-run `scripts/install.sh` from a RAILGUARDS checkout against this project, restart Cursor, and open a new chat. Do not install it yourself.
