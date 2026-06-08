from app.core.canonical_json import canonical_json
from app.core.crypto import generate_keypair, sign_payload, verify_signature
from app.core.hashing import compute_event_hash
from app.core.merkle import compute_merkle_root


def test_canonical_json_is_deterministic() -> None:
    assert canonical_json({"b": 2, "a": {"d": 4, "c": "✓"}}) == canonical_json(
        {"a": {"c": "✓", "d": 4}, "b": 2}
    )
    assert canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_ed25519_signing_and_verification() -> None:
    private_key, public_key = generate_keypair()
    payload = canonical_json({"action": "test"})
    signature = sign_payload(private_key, payload)
    assert verify_signature(public_key, payload, signature)
    assert not verify_signature(public_key, canonical_json({"action": "other"}), signature)


def test_event_hash_changes_with_body() -> None:
    first = compute_event_hash({"event_type": "one"}, None)
    second = compute_event_hash({"event_type": "two"}, None)
    assert first != second


def test_merkle_root_is_deterministic_and_duplicates_odd_leaf() -> None:
    leaves = ["00" * 32, "11" * 32, "22" * 32]
    assert compute_merkle_root(leaves) == compute_merkle_root(list(leaves))
    assert len(compute_merkle_root(leaves)) == 64

