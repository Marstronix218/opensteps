import json
from typing import Any


def canonical_json(data: dict[str, Any]) -> bytes:
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def without_fields(data: dict[str, Any], *fields: str) -> dict[str, Any]:
    excluded = set(fields)
    return {key: value for key, value in data.items() if key not in excluded}

