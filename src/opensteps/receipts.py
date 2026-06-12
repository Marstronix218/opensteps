"""Agent Action Receipts: construction, Ed25519 signing, and the append-only chain.

Format contract (normative copy in docs/SCHEMA.md):
- The receipt body is every field except "signature".
- signature = base64(Ed25519-sign(JCS(body))).
- receipt_hash = sha256_hex(JCS(full receipt, signature included)); the next
  receipt's prev_hash, so the chain also covers signatures.
"""

import base64
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from opensteps import RECEIPT_VERSION
from opensteps.canonical import canonical_bytes, sha256_hex


def _utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def build_receipt(
    *,
    prev_hash: str | None,
    agent_id: str,
    agent_framework: str,
    server: str,
    tool: str,
    request_hash: str,
    response_hash: str | None,
    rule_id: str,
    decision: str,
    approver_id: str | None = None,
    approver_method: str = "none",
    approver_decision: str | None = None,
    timestamp: str | None = None,
) -> dict:
    """Build an unsigned receipt body (all schema fields except signature)."""
    return {
        "version": RECEIPT_VERSION,
        "receipt_id": str(uuid.uuid4()),
        "prev_hash": prev_hash,
        "timestamp": timestamp or _utc_now_rfc3339(),
        "agent": {"id": agent_id, "framework": agent_framework},
        "tool": {"server": server, "name": tool},
        "request_hash": request_hash,
        "response_hash": response_hash,
        "policy": {"rule_id": rule_id, "decision": decision},
        "approver": {
            "id": approver_id,
            "method": approver_method,
            "decision": approver_decision,
        },
        "chain_head_anchor": None,
    }


def sign_receipt(body: dict, private_key: Ed25519PrivateKey) -> dict:
    """Return the receipt: body plus base64 Ed25519 signature over JCS(body)."""
    signature = private_key.sign(canonical_bytes(body))
    return {**body, "signature": base64.b64encode(signature).decode("ascii")}


def receipt_hash(receipt: dict) -> str:
    """Hash that the next receipt's prev_hash must equal."""
    return sha256_hex(canonical_bytes(receipt))


class ChainWriter:
    """Appends signed receipts to a JSONL file, maintaining the hash chain.

    If the log file already contains receipts, the chain resumes from the last
    line. Writes are flushed and fsynced per receipt; emission order defines
    chain order, so callers must serialize calls to append() (the proxy holds
    an asyncio.Lock).
    """

    def __init__(
        self,
        path: Path,
        private_key: Ed25519PrivateKey,
        *,
        agent_id: str,
        framework: str,
        server_name: str,
    ):
        self.path = Path(path)
        self._private_key = private_key
        self._agent_id = agent_id
        self._framework = framework
        self._server_name = server_name
        self._prev_hash = self._tail_hash()

    def _tail_hash(self) -> str | None:
        if not self.path.exists():
            return None
        last_line = None
        with self.path.open("rb") as f:
            for line in f:
                if line.strip():
                    last_line = line
        if last_line is None:
            return None
        return receipt_hash(json.loads(last_line))

    def append(
        self,
        *,
        tool: str,
        request_hash: str,
        response_hash: str | None,
        rule_id: str,
        decision: str,
        approver_id: str | None = None,
        approver_method: str = "none",
        approver_decision: str | None = None,
    ) -> dict:
        body = build_receipt(
            prev_hash=self._prev_hash,
            agent_id=self._agent_id,
            agent_framework=self._framework,
            server=self._server_name,
            tool=tool,
            request_hash=request_hash,
            response_hash=response_hash,
            rule_id=rule_id,
            decision=decision,
            approver_id=approver_id,
            approver_method=approver_method,
            approver_decision=approver_decision,
        )
        receipt = sign_receipt(body, self._private_key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self._prev_hash = receipt_hash(receipt)
        return receipt
