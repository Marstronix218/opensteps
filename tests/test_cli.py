import json
import subprocess
import sys

from opensteps.keys import generate_keypair, load_private_key
from opensteps.receipts import ChainWriter


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "opensteps", *args],
        capture_output=True, text=True,
    )


def make_chain(tmp_path, n=2):
    priv_path, pub_path = generate_keypair(tmp_path / "keys")
    log = tmp_path / "receipts.jsonl"
    writer = ChainWriter(log, load_private_key(priv_path),
                         agent_id="a", framework="f", server_name="s")
    for i in range(n):
        writer.append(tool=f"t{i}", request_hash=str(i) * 64, response_hash=None,
                      rule_id="r", decision="deny")
    return log, pub_path


def test_keygen_then_verify_valid_chain(tmp_path):
    result = run_cli("keygen", "--out-dir", str(tmp_path / "fresh"))
    assert result.returncode == 0
    assert (tmp_path / "fresh" / "signing.key").exists()

    log, pub_path = make_chain(tmp_path)
    result = run_cli("verify", str(log), "--pubkey", str(pub_path))
    assert result.returncode == 0
    assert "VALID" in result.stdout
    assert "2 receipts" in result.stdout


def test_verify_tampered_chain_exits_1(tmp_path):
    log, pub_path = make_chain(tmp_path)
    receipts = [json.loads(line) for line in log.read_text().splitlines()]
    receipts[0]["policy"]["decision"] = "allow"
    log.write_text("".join(json.dumps(r) + "\n" for r in receipts))

    result = run_cli("verify", str(log), "--pubkey", str(pub_path))
    assert result.returncode == 1
    assert "INVALID" in result.stdout
    assert "signature" in result.stdout


def test_verify_single_receipt(tmp_path):
    log, pub_path = make_chain(tmp_path, n=1)
    single = tmp_path / "one.json"
    single.write_text(log.read_text().splitlines()[0])
    result = run_cli("verify", str(single), "--pubkey", str(pub_path), "--single")
    assert result.returncode == 0


def test_missing_args_exit_2(tmp_path):
    assert run_cli("verify").returncode == 2
    assert run_cli("wrap", "--policy", "x", "--key", "y", "--log", "z").returncode == 2
