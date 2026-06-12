"""Offline verification of receipt chains.

This is the independence claim of the whole product: given a JSONL chain and a
public key, recompute every signature and every prev_hash link with no network,
no database, and no trust in the operator. Anyone can reimplement this module
from docs/SCHEMA.md; keep it free of imports beyond stdlib, cryptography, and
the canonicalization helpers.
"""

import base64
import json
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from opensteps.canonical import canonical_bytes
from opensteps.receipts import receipt_hash

REQUIRED_FIELDS = (
    "version",
    "receipt_id",
    "prev_hash",
    "timestamp",
    "agent",
    "tool",
    "request_hash",
    "response_hash",
    "policy",
    "approver",
    "chain_head_anchor",
    "signature",
)


@dataclass
class VerificationResult:
    valid: bool
    receipts_checked: int
    error_index: int | None = None
    error_receipt_id: str | None = None
    error_reason: str | None = None
    head_hash: str | None = None


def verify_receipt(receipt: dict, public_key: Ed25519PublicKey) -> tuple[bool, str]:
    """Structural and signature check of a single receipt (no chain context)."""
    if not isinstance(receipt, dict):
        return False, "receipt is not a JSON object"
    for field in REQUIRED_FIELDS:
        if field not in receipt:
            return False, f"missing required field '{field}'"
    body = {k: v for k, v in receipt.items() if k != "signature"}
    try:
        signature = base64.b64decode(receipt["signature"], validate=True)
    except Exception:
        return False, "signature is not valid base64"
    try:
        public_key.verify(signature, canonical_bytes(body))
    except InvalidSignature:
        return False, "signature does not verify against the receipt body"
    return True, "ok"


def verify_chain(path: Path, public_key: Ed25519PublicKey) -> VerificationResult:
    """Verify a JSONL receipt chain end to end."""
    prev_hash: str | None = None
    checked = 0
    with Path(path).open("r", encoding="utf-8") as f:
        for index, line in enumerate(line for line in f if line.strip()):
            try:
                receipt = json.loads(line)
            except json.JSONDecodeError:
                return VerificationResult(
                    valid=False,
                    receipts_checked=checked,
                    error_index=index,
                    error_reason="line is not valid JSON",
                )

            ok, reason = verify_receipt(receipt, public_key)
            if not ok:
                return VerificationResult(
                    valid=False,
                    receipts_checked=checked,
                    error_index=index,
                    error_receipt_id=receipt.get("receipt_id")
                    if isinstance(receipt, dict)
                    else None,
                    error_reason=reason,
                )

            if receipt["prev_hash"] != prev_hash:
                return VerificationResult(
                    valid=False,
                    receipts_checked=checked,
                    error_index=index,
                    error_receipt_id=receipt["receipt_id"],
                    error_reason=(
                        "prev_hash does not match the hash of the previous receipt "
                        "(missing, reordered, or rewritten receipt)"
                    ),
                )

            prev_hash = receipt_hash(receipt)
            checked += 1

    if checked == 0:
        return VerificationResult(
            valid=False, receipts_checked=0, error_reason="no receipts in file"
        )
    return VerificationResult(valid=True, receipts_checked=checked, head_hash=prev_hash)
