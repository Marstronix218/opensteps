"""Minimal stdlib-only MCP-ish server for e2e tests (newline JSON-RPC on stdio)."""

import json
import sys

TOOLS = [
    {
        "name": "echo",
        "description": "Echo text back",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
        },
    },
    {
        "name": "delete_everything",
        "description": "Dangerous tool the policy should block",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def reply(msg_id, result=None, error=None):
    response = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    print(json.dumps(response, separators=(",", ":")), flush=True)


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        method = msg.get("method")
        msg_id = msg.get("id")
        if msg_id is None:
            continue  # notification
        if method == "initialize":
            reply(msg_id, {
                "protocolVersion": (msg.get("params") or {}).get(
                    "protocolVersion", "2025-03-26"
                ),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "stub", "version": "0.0.1"},
            })
        elif method == "tools/list":
            reply(msg_id, {"tools": TOOLS})
        elif method == "tools/call":
            name = msg["params"]["name"]
            arguments = msg["params"].get("arguments") or {}
            if name == "echo":
                reply(msg_id, {
                    "content": [{"type": "text", "text": "echo: " + arguments.get("text", "")}],
                    "isError": False,
                })
            elif name == "delete_everything":
                reply(msg_id, {
                    "content": [{"type": "text", "text": "everything deleted"}],
                    "isError": False,
                })
            else:
                reply(msg_id, error={"code": -32602, "message": f"unknown tool {name}"})
        else:
            reply(msg_id, error={"code": -32601, "message": f"method not found: {method}"})


if __name__ == "__main__":
    main()
