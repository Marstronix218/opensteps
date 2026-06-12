import hashlib

from opensteps.canonical import canonical_bytes, hash_json, sha256_hex


def test_keys_are_sorted():
    assert canonical_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def test_key_order_does_not_matter():
    assert canonical_bytes({"x": 1, "y": 2}) == canonical_bytes({"y": 2, "x": 1})


def test_numbers_follow_jcs_rules():
    # RFC 8785 serializes numbers like ECMAScript: 10.0 -> 10
    assert canonical_bytes({"x": 10.0}) == b'{"x":10}'


def test_nested_structures_and_null():
    assert (
        canonical_bytes({"b": [1, {"d": None, "c": "x"}], "a": True})
        == b'{"a":true,"b":[1,{"c":"x","d":null}]}'
    )


def test_unicode_is_utf8_not_escaped():
    assert canonical_bytes({"k": "café"}) == '{"k":"café"}'.encode("utf-8")


def test_hash_json_matches_manual_sha256():
    obj = {"tool": "create_payment", "amount": 45000}
    expected = hashlib.sha256(canonical_bytes(obj)).hexdigest()
    assert hash_json(obj) == expected
    assert hash_json({"amount": 45000, "tool": "create_payment"}) == expected


def test_sha256_hex_is_lowercase_hex():
    digest = sha256_hex(b"opensteps")
    assert len(digest) == 64
    assert digest == digest.lower()
