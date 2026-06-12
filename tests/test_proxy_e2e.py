"""End-to-end: real proxy subprocess wrapping the stub server, raw JSON-RPC over stdio."""

import asyncio
import json
import sys
from pathlib import Path

import pytest

from opensteps.canonical import hash_json
from opensteps.keys import generate_keypair, load_public_key
from opensteps.verify import verify_chain

STUB = Path(__file__).parent / "mcp_stub_server.py"

POLICY = """
version: "0.1"
default: deny
rules:
  - id: allow-echo
    tool: echo
    action: allow
  - id: deny-deletes
    tool: delete_everything
    action: deny
"""


async def send(proc, msg):
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    await proc.stdin.drain()


async def recv(proc):
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=10)
    assert line, "proxy closed stdout unexpectedly"
    return json.loads(line)


@pytest.fixture
def workdir(tmp_path):
    generate_keypair(tmp_path / "keys")
    (tmp_path / "policy.yaml").write_text(POLICY)
    return tmp_path


async def start_proxy(workdir):
    return await asyncio.create_subprocess_exec(
        sys.executable, "-m", "opensteps", "wrap",
        "--policy", str(workdir / "policy.yaml"),
        "--key", str(workdir / "keys" / "signing.key"),
        "--log", str(workdir / "receipts.jsonl"),
        "--agent-id", "test-agent",
        "--server-name", "stub",
        "--", sys.executable, str(STUB),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )


async def test_proxy_end_to_end(workdir):
    proc = await start_proxy(workdir)
    try:
        # initialize passes through untouched and produces no receipt
        await send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {"protocolVersion": "2025-03-26"}})
        resp = await recv(proc)
        assert resp["id"] == 1
        assert resp["result"]["serverInfo"]["name"] == "stub"

        # tools/list passes through
        await send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        resp = await recv(proc)
        assert [t["name"] for t in resp["result"]["tools"]] == [
            "echo", "delete_everything"
        ]

        # allowed call: response intact, receipt written
        echo_params = {"name": "echo", "arguments": {"text": "hi"}}
        await send(proc, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                          "params": echo_params})
        resp = await recv(proc)
        assert resp["result"]["content"][0]["text"] == "echo: hi"
        assert resp["result"]["isError"] is False

        # denied call: never reaches the server, agent sees a tool error
        delete_params = {"name": "delete_everything", "arguments": {}}
        await send(proc, {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                          "params": delete_params})
        resp = await recv(proc)
        assert resp["id"] == 4
        assert resp["result"]["isError"] is True
        assert "deny-deletes" in resp["result"]["content"][0]["text"]

        proc.stdin.close()
        await asyncio.wait_for(proc.wait(), timeout=10)
    finally:
        if proc.returncode is None:
            proc.terminate()
            await proc.wait()

    # the chain: exactly the two tool calls, in order, independently verifiable
    lines = (workdir / "receipts.jsonl").read_text().splitlines()
    receipts = [json.loads(line) for line in lines]
    assert [r["policy"]["decision"] for r in receipts] == ["allow", "deny"]
    assert [r["policy"]["rule_id"] for r in receipts] == ["allow-echo", "deny-deletes"]
    assert [r["tool"]["name"] for r in receipts] == ["echo", "delete_everything"]
    assert receipts[0]["request_hash"] == hash_json(echo_params)
    assert receipts[0]["response_hash"] is not None
    assert receipts[1]["request_hash"] == hash_json(delete_params)
    assert receipts[1]["response_hash"] is None
    assert all(r["agent"]["id"] == "test-agent" for r in receipts)
    assert all(r["tool"]["server"] == "stub" for r in receipts)

    result = verify_chain(
        workdir / "receipts.jsonl",
        load_public_key(workdir / "keys" / "signing.pub"),
    )
    assert result.valid and result.receipts_checked == 2


async def test_proxy_passthrough_of_unknown_messages(workdir):
    proc = await start_proxy(workdir)
    try:
        # a notification (no id) is forwarded and the stub ignores it silently
        await send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        # an unknown method round-trips as a JSON-RPC error from the stub
        await send(proc, {"jsonrpc": "2.0", "id": 9, "method": "resources/list"})
        resp = await recv(proc)
        assert resp["id"] == 9
        assert resp["error"]["code"] == -32601

        proc.stdin.close()
        await asyncio.wait_for(proc.wait(), timeout=10)
    finally:
        if proc.returncode is None:
            proc.terminate()
            await proc.wait()

    # nothing was a tools/call -> no receipts at all
    assert not (workdir / "receipts.jsonl").exists()
