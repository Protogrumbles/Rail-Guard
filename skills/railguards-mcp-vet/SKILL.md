---
name: railguards-mcp-vet
description: Vet an MCP server before it is enabled or used, and return Allow, Allow with conditions, or Reject. Use when the user invokes /railguards-mcp-vet.
disable-model-invocation: true
---

# MCP vet

Find `railguards-vet/SKILL.md` in `.agents/skills/`, `.claude/skills/`, or `.cursor/skills/` and follow it. The subject is an MCP server: the config entry that launches it and the package, image, or URL it runs.

If the user named a server or a config file, vet that one. Otherwise read `.cursor/mcp.json`, `.mcp.json`, and `.claude/settings.json`, list the server names you find, and ask which one to vet before doing the review.

Do not install, enable, approve, or edit the MCP config as part of vetting. If RAILGUARDS is not installed, say so and stop.
