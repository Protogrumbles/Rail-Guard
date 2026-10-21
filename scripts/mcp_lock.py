#!/usr/bin/env python3
"""Pin approved MCP servers and detect changes after approval ("rug pulls").

The lock (.railguards/mcp-lock.json) stores, per server, a hash of its config
entry, whether its package is pinned, and (when known) each tool definition
with its hash. Tool definitions come from --tools-file (JSON object mapping
server name to a list of tools) or from --probe, which starts each configured
stdio server and calls tools/list.

Usage:
  mcp_lock.py snapshot [--config PATH ...] [--tools-file FILE] [--probe] [--lock FILE]
  mcp_lock.py verify   [--config PATH ...] [--tools-file FILE] [--probe] [--lock FILE]
`verify` exits 1 when drift is found.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_unicode import scan_text  # noqa: E402

DEFAULT_CONFIGS = [".cursor/mcp.json", ".mcp.json"]
DEFAULT_LOCK = ".railguards/mcp-lock.json"
PROTOCOL_VERSION = "2025-06-18"
ENV_REF = re.compile(r"\$\{(?:env:)?([A-Za-z_][A-Za-z0-9_]*)\}")


def sha256(obj) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _npm_spec_pinned(spec: str) -> bool:
    name, _, version = spec[1:].partition("@") if spec.startswith("@") else spec.partition("@")
    return bool(version) and version not in ("latest", "next", "*") and bool(re.match(r"^\d", version))


def is_pinned(entry: dict) -> bool | None:
    """True/False for known package launchers, None when it cannot be judged."""
    command = Path(str(entry.get("command", ""))).name
    args = [str(a) for a in entry.get("args", [])]
    positional = [a for a in args if not a.startswith("-")]
    if command in ("npx", "bunx", "pnpx") or (command in ("pnpm", "yarn") and args[:1] == ["dlx"]):
        if command in ("pnpm", "yarn"):
            positional = positional[1:]
        return _npm_spec_pinned(positional[0]) if positional else False
    if command in ("uvx", "pipx"):
        if "--from" in args:
            idx = args.index("--from")
            return idx + 1 < len(args) and "==" in args[idx + 1]
        if command == "pipx" and positional[:1] == ["run"]:
            positional = positional[1:]
        return bool(positional) and "==" in positional[0]
    if command in ("docker", "podman"):
        images = [a for a in positional if a != "run" and "=" not in a and ("/" in a or "@" in a or ":" in a)]
        return bool(images) and "@sha256:" in images[0]
    return None


def load_servers(config_paths) -> dict:
    servers = {}
    for path in config_paths:
        path = Path(path)
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, entry in (data.get("mcpServers") or {}).items():
            servers[name] = {"source": path.as_posix(), "entry": entry}
    return servers


def _tool_warnings(tools: list[dict]) -> list[str]:
    warnings = []
    for tool in tools:
        text = json.dumps(tool, ensure_ascii=False)
        for finding in scan_text(text):
            warnings.append(f"{tool.get('name', '?')}: hidden character {finding['codepoint']} ({finding['category']})")
    return warnings


def snapshot(config_paths, tools_by_server: dict | None) -> dict:
    lock = {"version": 1, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "servers": {}}
    for name, info in sorted(load_servers(config_paths).items()):
        entry = info["entry"]
        record = {
            "source": info["source"],
            "transport": "http" if "url" in entry else "stdio",
            "config_hash": sha256(entry),
            "pinned": is_pinned(entry),
            "warnings": [],
        }
        tools = (tools_by_server or {}).get(name)
        if tools is not None:
            record["tools"] = tools
            record["tool_hashes"] = {t.get("name", f"#{i}"): sha256(t) for i, t in enumerate(tools)}
            record["warnings"] = _tool_warnings(tools)
        lock["servers"][name] = record
    return lock


def verify(lock: dict, config_paths, tools_by_server: dict | None) -> list[str]:
    drift = []
    current = load_servers(config_paths)
    locked = lock.get("servers", {})
    for name in sorted(set(current) - set(locked)):
        drift.append(f"{name}: new server not in lock (vet it, then re-run snapshot)")
    for name in sorted(set(locked) - set(current)):
        drift.append(f"{name}: server in lock but no longer configured")
    for name in sorted(set(current) & set(locked)):
        if sha256(current[name]["entry"]) != locked[name].get("config_hash"):
            drift.append(f"{name}: configuration changed since approval")
        tools = (tools_by_server or {}).get(name)
        if tools is None or "tool_hashes" not in locked[name]:
            continue
        now = {t.get("name", f"#{i}"): sha256(t) for i, t in enumerate(tools)}
        before = locked[name]["tool_hashes"]
        for tool in sorted(set(now) - set(before)):
            drift.append(f"{name}/{tool}: new tool not in lock")
        for tool in sorted(set(before) - set(now)):
            drift.append(f"{name}/{tool}: tool removed")
        for tool in sorted(set(now) & set(before)):
            if now[tool] != before[tool]:
                drift.append(f"{name}/{tool}: tool definition changed since approval")
        for warning in _tool_warnings(tools):
            drift.append(f"{name}/{warning}")
    return drift


def _expand_env(value: str) -> str:
    return ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), value)


def probe_stdio(entry: dict, timeout: float = 20.0) -> list[dict]:
    """Start a stdio MCP server, run initialize + tools/list, and return its tools."""
    if "command" not in entry:
        raise ValueError("only stdio servers (with a command) can be probed")
    env = dict(os.environ)
    env.update({k: _expand_env(str(v)) for k, v in (entry.get("env") or {}).items()})
    cmd = [entry["command"], *[_expand_env(str(a)) for a in entry.get("args", [])]]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env)
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    try:
        def request(msg_id: int, method: str, params: dict) -> dict:
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}) + "\n")
            proc.stdin.flush()
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                msg = json.loads(line)
                if msg.get("id") == msg_id:
                    if "error" in msg:
                        raise RuntimeError(f"{method} failed: {msg['error']}")
                    return msg.get("result", {})
            raise RuntimeError(f"server exited before answering {method}")

        request(1, "initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "railguards-mcp-lock", "version": "1"}})
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()
        tools, cursor, msg_id = [], None, 2
        while True:
            result = request(msg_id, "tools/list", {"cursor": cursor} if cursor else {})
            tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            msg_id += 1
            if not cursor:
                return tools
    finally:
        timer.cancel()
        proc.kill()
        proc.wait()
        proc.stdin.close()
        proc.stdout.close()


def _gather_tools(args, config_paths) -> dict | None:
    tools = None
    if args.tools_file:
        tools = json.loads(Path(args.tools_file).read_text(encoding="utf-8"))
    if args.probe:
        tools = dict(tools or {})
        for name, info in load_servers(config_paths).items():
            if name in tools or "command" not in info["entry"]:
                continue
            try:
                tools[name] = probe_stdio(info["entry"])
            except Exception as exc:  # noqa: BLE001 - report and continue
                print(f"warning: could not probe {name}: {exc}", file=sys.stderr)
    return tools


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["snapshot", "verify"])
    parser.add_argument("--config", action="append", help="MCP config file (repeatable)")
    parser.add_argument("--tools-file", help="JSON mapping server name to its tools/list result")
    parser.add_argument("--probe", action="store_true", help="start stdio servers to list their tools")
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    args = parser.parse_args(argv)

    config_paths = args.config or DEFAULT_CONFIGS
    tools = _gather_tools(args, config_paths)
    lock_path = Path(args.lock)

    if args.command == "snapshot":
        lock = snapshot(config_paths, tools)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for name, server in lock["servers"].items():
            pinned = {True: "pinned", False: "UNPINNED", None: "pinning unknown"}[server["pinned"]]
            count = len(server.get("tools", [])) if "tools" in server else "unknown"
            print(f"{name}: {pinned}, tools: {count}")
            for warning in server["warnings"]:
                print(f"  warning: {warning}")
        print(f"Lock written to {lock_path}")
        return 0

    if not lock_path.is_file():
        print(f"No lock at {lock_path}; run snapshot first.", file=sys.stderr)
        return 1
    drift = verify(json.loads(lock_path.read_text(encoding="utf-8")), config_paths, tools)
    for line in drift:
        print(line)
    if not drift:
        print("No drift: MCP configuration matches the lock.")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
