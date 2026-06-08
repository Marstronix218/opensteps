import hashlib
from typing import Any

from app.core.canonical_json import canonical_json, without_fields


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_json(data: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(data))


def compute_event_hash(event_body: dict[str, Any], previous_hash: str | None) -> str:
    body = without_fields(event_body, "event_hash")
    envelope = {"event": body, "previous_hash": previous_hash}
    return sha256_hex(canonical_json(envelope))

