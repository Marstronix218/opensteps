"""The OpenSteps launch demo, end to end.

1. An AI bookkeeper processes invoices through the OpenSteps proxy.
2. A poisoned invoice prompt-injects it into attempting a $45,000 payment.
3. Policy blocks the payment — and the *blocked attempt* becomes a signed receipt.
4. `opensteps verify` proves the whole chain with just the public key.
5. Tampering with the chain (editing a decision, deleting a receipt) is caught.

Maps to OWASP Agentic Top 10: ASI01 (goal hijack), ASI02 (tool misuse).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo" / "out"


def banner(text: str):
    print(f"\n=== {text} " + "=" * max(0, 64 - len(text)), flush=True)


def run_verify(chain: Path, pubkey: Path) -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "opensteps", "verify", str(chain),
         "--pubkey", str(pubkey)],
        capture_output=True, text=True,
    )
    print(proc.stdout.rstrip(), flush=True)
    return proc.returncode


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    banner("1. keygen")
    subprocess.run(
        [sys.executable, "-m", "opensteps", "keygen",
         "--out-dir", str(OUT / "keys")],
        check=True,
    )

    banner("2. a prompt-injected bookkeeping agent, behind OpenSteps")
    agent = subprocess.run([sys.executable, str(ROOT / "demo" / "agent.py"), str(OUT)])
    if agent.returncode != 0:
        print("demo agent failed", file=sys.stderr)
        return 1

    chain = OUT / "receipts.jsonl"
    pubkey = OUT / "keys" / "signing.pub"
    receipts = [json.loads(line) for line in chain.read_text().splitlines()]

    banner("3. the receipt chain (one line per tool call)")
    for i, r in enumerate(receipts):
        print(f"  {i}: {r['tool']['name']:<22} {r['policy']['decision']:<6} "
              f"rule={r['policy']['rule_id']}")
    blocked = [r for r in receipts if r["policy"]["decision"] == "deny"]
    if len(blocked) != 1:
        print("expected exactly one denied call", file=sys.stderr)
        return 1

    banner("4. anyone can verify — public key only, no network, no account")
    if run_verify(chain, pubkey) != 0:
        print("verification should have passed", file=sys.stderr)
        return 1

    banner("5. tampering is detectable: flip the blocked payment to 'allow'")
    edited = OUT / "tampered_edited.jsonl"
    tampered = [dict(r) for r in receipts]
    for r in tampered:
        if r["policy"]["decision"] == "deny":
            r["policy"] = {**r["policy"], "decision": "allow"}
    edited.write_text("".join(json.dumps(r) + "\n" for r in tampered))
    if run_verify(edited, pubkey) != 1:
        print("edited chain should have failed verification", file=sys.stderr)
        return 1

    banner("6. tampering is detectable: quietly delete the blocked attempt")
    deleted = OUT / "tampered_deleted.jsonl"
    deleted.write_text(
        "".join(json.dumps(r) + "\n" for r in receipts
                if r["policy"]["decision"] != "deny")
    )
    if run_verify(deleted, pubkey) != 1:
        print("truncated chain should have failed verification", file=sys.stderr)
        return 1

    banner("what just happened")
    print(
        "  A poisoned invoice hijacked the agent (OWASP Agentic ASI01) into\n"
        "  attempting an unauthorized $45,000 payment (ASI02). OpenSteps blocked\n"
        "  it under rule 'deny-unapproved-payments', and the blocked attempt is\n"
        "  itself a signed receipt in the chain. Send anyone\n"
        f"    {chain}\n"
        f"    {pubkey}\n"
        "  and they can run `opensteps verify` themselves — no trust in this\n"
        "  machine, this operator, or OpenSteps required.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
