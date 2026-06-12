import json

import pytest

from opensteps.keys import generate_keypair, load_private_key, load_public_key
from opensteps.receipts import ChainWriter
from opensteps.verify import verify_chain, verify_receipt


@pytest.fixture
def chain(tmp_path):
    priv_path, pub_path = generate_keypair(tmp_path / "keys")
    private_key = load_private_key(priv_path)
    public_key = load_public_key(pub_path)
    log = tmp_path / "receipts.jsonl"
    writer = ChainWriter(log, private_key, agent_id="a", framework="f", server_name="s")
    for i, decision in enumerate(["allow", "deny", "allow"]):
        writer.append(
            tool=f"tool_{i}",
            request_hash=str(i) * 64,
            response_hash=None if decision == "deny" else "e" * 64,
            rule_id=f"rule-{i}",
            decision=decision,
        )
    return log, public_key, private_key


def read_receipts(log):
    return [json.loads(line) for line in log.read_text().splitlines()]


def write_receipts(log, receipts):
    log.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in receipts))


def test_valid_chain_verifies(chain):
    log, public_key, _ = chain
    result = verify_chain(log, public_key)
    assert result.valid
    assert result.receipts_checked == 3
    assert result.error_index is None


def test_edited_field_breaks_signature(chain):
    log, public_key, _ = chain
    receipts = read_receipts(log)
    receipts[1]["policy"]["decision"] = "allow"  # flip the deny
    write_receipts(log, receipts)
    result = verify_chain(log, public_key)
    assert not result.valid
    assert result.error_index == 1
    assert "signature" in result.error_reason


def test_deleted_receipt_breaks_chain(chain):
    log, public_key, _ = chain
    receipts = read_receipts(log)
    del receipts[1]
    write_receipts(log, receipts)
    result = verify_chain(log, public_key)
    assert not result.valid
    assert result.error_index == 1
    assert "prev_hash" in result.error_reason


def test_reordered_receipts_break_chain(chain):
    log, public_key, _ = chain
    receipts = read_receipts(log)
    receipts[1], receipts[2] = receipts[2], receipts[1]
    write_receipts(log, receipts)
    result = verify_chain(log, public_key)
    assert not result.valid
    assert result.error_index == 1
    assert "prev_hash" in result.error_reason


def test_forged_receipt_with_other_key_fails(chain, tmp_path):
    log, public_key, _ = chain
    attacker_priv, _ = generate_keypair(tmp_path / "attacker")
    attacker_key = load_private_key(attacker_priv)
    receipts = read_receipts(log)

    from opensteps.receipts import sign_receipt

    body = {k: v for k, v in receipts[1].items() if k != "signature"}
    body["response_hash"] = "f" * 64
    receipts[1] = sign_receipt(body, attacker_key)
    write_receipts(log, receipts)
    result = verify_chain(log, public_key)
    assert not result.valid
    assert result.error_index == 1
    assert "signature" in result.error_reason


def test_wrong_public_key_fails_at_genesis(chain, tmp_path):
    log, _, _ = chain
    _, other_pub = generate_keypair(tmp_path / "other")
    result = verify_chain(log, load_public_key(other_pub))
    assert not result.valid
    assert result.error_index == 0


def test_garbage_line_reports_structure_error(chain):
    log, public_key, _ = chain
    log.write_text(log.read_text() + "not json\n")
    result = verify_chain(log, public_key)
    assert not result.valid
    assert result.error_index == 3
    assert "JSON" in result.error_reason


def test_missing_field_reports_structure_error(chain):
    log, public_key, _ = chain
    receipts = read_receipts(log)
    del receipts[2]["request_hash"]
    write_receipts(log, receipts)
    result = verify_chain(log, public_key)
    assert not result.valid
    assert result.error_index == 2
    assert "request_hash" in result.error_reason


def test_empty_file_is_invalid(tmp_path):
    _, pub_path = generate_keypair(tmp_path / "keys")
    log = tmp_path / "empty.jsonl"
    log.write_text("")
    result = verify_chain(log, load_public_key(pub_path))
    assert not result.valid
    assert "no receipts" in result.error_reason


def test_single_receipt_signature_check(chain):
    log, public_key, _ = chain
    receipts = read_receipts(log)
    ok, reason = verify_receipt(receipts[2], public_key)
    assert ok
    receipts[2]["tool"]["name"] = "evil"
    ok, reason = verify_receipt(receipts[2], public_key)
    assert not ok
    assert "signature" in reason
