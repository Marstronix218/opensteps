import stat

import pytest
from cryptography.exceptions import InvalidSignature

from opensteps.keys import generate_keypair, load_private_key, load_public_key


def test_generate_creates_both_files(tmp_path):
    priv_path, pub_path = generate_keypair(tmp_path)
    assert priv_path.name == "signing.key"
    assert pub_path.name == "signing.pub"
    assert priv_path.exists() and pub_path.exists()


def test_private_key_is_owner_only(tmp_path):
    priv_path, _ = generate_keypair(tmp_path)
    mode = stat.S_IMODE(priv_path.stat().st_mode)
    assert mode == 0o600


def test_sign_verify_round_trip(tmp_path):
    priv_path, pub_path = generate_keypair(tmp_path)
    private_key = load_private_key(priv_path)
    public_key = load_public_key(pub_path)
    sig = private_key.sign(b"hello receipts")
    public_key.verify(sig, b"hello receipts")  # raises if invalid
    with pytest.raises(InvalidSignature):
        public_key.verify(sig, b"tampered")


def test_keys_are_pem(tmp_path):
    priv_path, pub_path = generate_keypair(tmp_path)
    assert b"BEGIN PRIVATE KEY" in priv_path.read_bytes()
    assert b"BEGIN PUBLIC KEY" in pub_path.read_bytes()


def test_loading_public_as_private_fails(tmp_path):
    _, pub_path = generate_keypair(tmp_path)
    with pytest.raises(ValueError):
        load_private_key(pub_path)
