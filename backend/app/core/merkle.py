from app.core.hashing import sha256_hex


def compute_merkle_root(event_hashes: list[str]) -> str:
    if not event_hashes:
        raise ValueError("Cannot compute a Merkle root without event hashes")
    level = [bytes.fromhex(item) for item in event_hashes]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            bytes.fromhex(sha256_hex(level[index] + level[index + 1]))
            for index in range(0, len(level), 2)
        ]
    return level[0].hex()

