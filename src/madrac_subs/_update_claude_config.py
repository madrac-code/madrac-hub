"""Update claude_desktop_config.json with the correct MADRAC MCP server entry."""
import json
import os
import sys

appdata = os.environ["APPDATA"]
path = os.path.join(appdata, "Claude", "claude_desktop_config.json")

with open(path, "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

cfg.setdefault("mcpServers", {})
cfg["mcpServers"]["madrac-subs"] = {
    "command": sys.argv[1],
    "args": ["-m", "madrac.mcp"],
    "cwd": sys.argv[2],
}

with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

# Verify round-trip
with open(path, "r", encoding="utf-8-sig") as f:
    d = json.load(f)
entry = d["mcpServers"]["madrac-subs"]
print(f"Command: {entry['command']}")
print(f"  exists: {os.path.exists(entry['command'])}")
print(f"CWD: {entry['cwd']}")
print(f"  exists: {os.path.exists(entry['cwd'])}")
print("Config updated OK")
