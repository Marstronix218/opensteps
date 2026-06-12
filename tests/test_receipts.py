import base64
import json
import re

from opensteps.canonical import canonical_bytes, sha256_hex
from opensteps.keys import generate_keypair, load_private_key, load_public_key
from opensteps.receipts import ChainWriter, build_receipt, receipt_hash, sign_receipt

RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def make_keys(tmp_path):
    priv_path, pub_path = generate_keypair(tmp_path / "keys")
    return load_private_key(priv_path), load_public_key(pub_path)


def make_body(prev_hash=None):
    return build_receipt(
        prev_hash=prev_hash,
        agent_id="agent-1",
        agent_framework="test",
        server="books",
        tool="create_payment",
        request_hash="a" * 64,
        response_hash=None,
        rule_id="deny-payments",
        decision="deny",
    )


def test_body_has_all_schema_fields():
    body = make_body()
    assert set(body) == {
        "version", "receipt_id", "prev_hash", "timestamp", "agent", "tool",
        "request_hash", "response_hash", "policy", "approver", "chain_head_anchor",
    }
    assert body["version"] == "0.1"
    assert body["agent"] == {"id": "agent-1", "framework": "test"}
    assert body["tool"] == {"server": "books", "name": "create_payment"}
    assert body["policy"] == {"rule_id": "deny-payments", "decision": "deny"}
    assert body["approver"] == {"id": None, "method": "none", "decision": None}
    assert body["chain_head_anchor"] is None
    assert RFC3339_UTC.match(body["timestamp"])


def test_signature_verifies_over_body_without_signature(tmp_path):
    private_key, public_key = make_keys(tmp_path)
    receipt = sign_receipt(make_body(), private_key)
    body = {k: v for k, v in receipt.items() if k != "signature"}
    public_key.verify(
        base64.b64decode(receipt["signature"]), canonical_bytes(body)
    )  # raises if invalid


def test_receipt_hash_covers_signature(tmp_path):
    private_key, _ = make_keys(tmp_path)
    receipt = sign_receipt(make_body(), private_key)
    assert receipt_hash(receipt) == sha256_hex(canonical_bytes(receipt))


def test_chain_writer_links_receipts(tmp_path):
    private_key, _ = make_keys(tmp_path)
    log = tmp_path / "receipts.jsonl"
    writer = ChainWriter(log, private_key, agent_id="a", framework="f", server_name="s")
    r1 = writer.append(tool="t1", request_hash="1" * 64, response_hash="2" * 64,
                       rule_id="r", decision="allow")
    r2 = writer.append(tool="t2", request_hash="3" * 64, response_hash=None,
                       rule_id="r2", decision="deny")
    r3 = writer.append(tool="t3", request_hash="4" * 64, response_hash="5" * 64,
                       rule_id="r3", decision="approve", approver_id="nori",
                       approver_method="cli", approver_decision="approved")

    lines = log.read_text().splitlines()
    assert len(lines) == 3
    parsed = [json.loads(line) for line in lines]
    assert parsed[0]["prev_hash"] is None
    assert parsed[1]["prev_hash"] == receipt_hash(parsed[0])
    assert parsed[2]["prev_hash"] == receipt_hash(parsed[1])
    assert [p["receipt_id"] for p in parsed] == [
        r1["receipt_id"], r2["receipt_id"], r3["receipt_id"]
    ]
    assert parsed[2]["approver"] == {
        "id": "nori", "method": "cli", "decision": "approved"
    }


def test_chain_writer_resumes_existing_chain(tmp_path):
    private_key, _ = make_keys(tmp_path)
    log = tmp_path / "receipts.jsonl"
    writer = ChainWriter(log, private_key, agent_id="a", framework="f", server_name="s")
    writer.append(tool="t1", request_hash="1" * 64, response_hash=None,
                  rule_id="r", decision="deny")
    last = writer.append(tool="t2", request_hash="2" * 64, response_hash=None,
                         rule_id="r", decision="deny")

    resumed = ChainWriter(log, private_key, agent_id="a", framework="f", server_name="s")
    r3 = resumed.append(tool="t3", request_hash="3" * 64, response_hash=None,
                        rule_id="r", decision="deny")
    assert r3["prev_hash"] == receipt_hash(last)
    assert len(log.read_text().splitlines()) == 3
