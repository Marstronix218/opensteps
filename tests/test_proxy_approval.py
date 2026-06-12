"""The approve path through the proxy, with an injected approval function."""

import json

import pytest

from opensteps.approval import ApprovalResult
from opensteps.canonical import hash_json
from opensteps.keys import generate_keypair, load_private_key
from opensteps.policy import Policy
from opensteps.proxy import MCPProxy
from opensteps.receipts import ChainWriter

POLICY = """
version: "0.1"
default: deny
rules:
  - id: payments-need-approval
    tool: create_payment
    action: approve
"""


@pytest.fixture
def setup(tmp_path):
    priv_path, _ = generate_keypair(tmp_path / "keys")
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(POLICY)
    log = tmp_path / "receipts.jsonl"

    def build(approval_fn):
        writer = ChainWriter(
            log, load_private_key(priv_path),
            agent_id="a", framework="f", server_name="books",
        )
        proxy = MCPProxy(
            server_cmd=["unused"],
            policy=Policy.load(policy_path),
            chain_writer=writer,
            server_name="books",
            approval_fn=approval_fn,
        )
        sent_to_server, sent_to_client = [], []

        async def fake_write_server(raw):
            sent_to_server.append(json.loads(raw))

        async def fake_write_client(raw):
            sent_to_client.append(json.loads(raw))

        proxy._write_server = fake_write_server
        proxy._write_client = fake_write_client
        return proxy, sent_to_server, sent_to_client

    return build, log


CALL = {
    "jsonrpc": "2.0",
    "id": 7,
    "method": "tools/call",
    "params": {"name": "create_payment", "arguments": {"payee": "Acme", "amount": 100}},
}


async def test_approved_call_is_forwarded_and_receipted(setup):
    build, log = setup
    proxy, to_server, to_client = build(
        lambda *a, **k: ApprovalResult(approved=True, approver_id="nori", method="cli")
    )
    await proxy._handle_client_line(json.dumps(CALL).encode())
    assert to_server and to_server[0]["id"] == 7  # forwarded
    assert not to_client

    # server responds -> receipt carries the approver
    response = {"jsonrpc": "2.0", "id": 7,
                "result": {"content": [{"type": "text", "text": "paid"}],
                           "isError": False}}
    await proxy._handle_server_line(json.dumps(response).encode())
    assert to_client and to_client[0]["id"] == 7

    receipt = json.loads(log.read_text().splitlines()[0])
    assert receipt["policy"] == {"rule_id": "payments-need-approval",
                                 "decision": "approve"}
    assert receipt["approver"] == {"id": "nori", "method": "cli",
                                   "decision": "approved"}
    assert receipt["response_hash"] == hash_json(response["result"])


async def test_rejected_call_is_blocked_and_receipted(setup):
    build, log = setup
    proxy, to_server, to_client = build(
        lambda *a, **k: ApprovalResult(approved=False, approver_id="nori", method="cli")
    )
    await proxy._handle_client_line(json.dumps(CALL).encode())
    assert not to_server  # never reached the wrapped server
    assert to_client[0]["result"]["isError"] is True
    assert "rejected" in to_client[0]["result"]["content"][0]["text"]

    receipt = json.loads(log.read_text().splitlines()[0])
    assert receipt["policy"]["decision"] == "approve"
    assert receipt["approver"] == {"id": "nori", "method": "cli",
                                   "decision": "rejected"}
    assert receipt["response_hash"] is None
