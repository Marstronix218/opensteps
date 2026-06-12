"""RFC 8785 (JCS) canonicalization and hashing.

Every hash in a receipt — request_hash, response_hash, prev_hash — and every
signature is computed over JCS bytes, so independent verifier implementations
hash identically. This module is the single source of truth for that.
"""

import hashlib

import rfc8785


def canonical_bytes(obj) -> bytes:
    """Serialize a JSON-compatible object to RFC 8785 canonical form."""
    return rfc8785.dumps(obj)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_json(obj) -> str:
    """Lowercase-hex SHA-256 of the JCS serialization of obj."""
    return sha256_hex(canonical_bytes(obj))
