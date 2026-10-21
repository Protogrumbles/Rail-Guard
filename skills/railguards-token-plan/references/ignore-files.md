# Ignore and deny configuration

Keep agents away from files that are large, generated or irrelevant. This is the cheapest token win and also reduces the chance of reading secrets.

## Cursor

- **`.cursorignore`**: files Cursor will not read or index (gitignore syntax). Use for generated, vendored, data and secret files.
- **`.cursorindexingignore`**: excluded from indexing only; the agent can still open them when asked. Use for large files that are occasionally relevant.
- Cursor also respects `.gitignore`.

## Claude Code

Use permission deny rules in `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": [
      "Read(./dist/**)",
      "Read(./**/*.min.js)",
      "Read(./.env)",
      "Read(./.env.*)"
    ]
  }
}
```

## Typical entries

Template: `templates/cursorignore`.

- Build output: `dist/`, `build/`, `out/`, `.next/`, `target/`, `coverage/`
- Dependencies: `node_modules/`, `vendor/`, `.venv/`, `venv/`
- Generated code: `*.generated.*`, `*_pb2.py`, `*.pb.go`, `generated/`
- Minified and maps: `*.min.js`, `*.min.css`, `*.map`
- Data and fixtures: `*.csv`, `*.parquet`, `*.sqlite`, large `fixtures/` and `__snapshots__/`
- Lockfiles: `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Cargo.lock` (agents rarely need to read them; dependency tools do)
- Secrets: `.env`, `.env.*` (keep `!.env.example`), `*.pem`, `*.key`

Check that tests and source the agent must edit are not accidentally excluded.
