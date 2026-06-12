# Agent Action Receipt — format v0.1 (normative)

This document is the complete contract for OpenSteps receipts. A verifier
written from this page alone, in any language, must accept every chain the
reference implementation produces and reject every tampered one. That
independence is the point: receipts are evidence precisely because checking
them requires no trust in the operator, their database, or OpenSteps itself.

## A receipt

One JSON object per line in an append-only JSONL file (UTF-8, `\n`-separated).

```json
{
  "version": "0.1",
  "receipt_id": "5f0e2c1a-0c8e-4a6b-9b1d-2f4a8c0d9e11",
  "prev_hash": "9c3f…64 hex chars… | null",
  "timestamp": "2026-06-11T09:30:00.123456Z",
  "agent": { "id": "bookkeeper-1", "framework": "demo-script" },
  "tool": { "server": "accounting", "name": "create_payment" },
  "request_hash": "64 lowercase hex chars",
  "response_hash": "64 lowercase hex chars | null",
  "policy": { "rule_id": "deny-unapproved-payments", "decision": "deny" },
  "approver": { "id": null, "method": "none", "decision": null },
  "chain_head_anchor": null,
  "signature": "base64"
}
```

| Field | Type | Meaning |
|---|---|---|
| `version` | string | Format version, `"0.1"`. |
| `receipt_id` | string | UUID v4, unique per receipt. |
| `prev_hash` | string \| null | SHA-256 (lowercase hex) of the **previous receipt**, computed as defined below. `null` only for the first receipt in a chain. |
| `timestamp` | string | RFC 3339 UTC with `Z` suffix, time the receipt was emitted. |
| `agent.id` | string | Operator-assigned identity of the agent. |
| `agent.framework` | string | Free-form framework label. |
| `tool.server` | string | Name of the wrapped MCP server (operator-assigned). |
| `tool.name` | string | Tool that was called. |
| `request_hash` | string | SHA-256 (hex) of the JCS bytes of the JSON-RPC `params` object of the `tools/call` request, i.e. `{"name": …, "arguments": …}`. |
| `response_hash` | string \| null | SHA-256 (hex) of the JCS bytes of the JSON-RPC `result` object the wrapped server returned (tool errors included). If the server answered with a protocol-level `error` object instead, the hash is over that object. `null` when the call was denied or rejected and never reached the server. |
| `policy.rule_id` | string | The matched rule's id, or `"default"`. |
| `policy.decision` | string | `"allow"`, `"deny"`, or `"approve"` (approval was required). |
| `approver.id` | string \| null | Who answered the approval prompt (`null` if none). |
| `approver.method` | string | `"cli"` or `"none"` (`"slack"` reserved). |
| `approver.decision` | string \| null | `"approved"`, `"rejected"`, or `null` when no approval was involved. Extension over the thesis sketch: without it a receipt cannot distinguish an approval from a rejection. |
| `chain_head_anchor` | string \| null | Transparency-log entry id (trust-ladder Rung 2). Always `null` in v0.1. |
| `signature` | string | Standard base64 of an Ed25519 signature, defined below. |

Note that receipts store **hashes** of requests and responses, not payloads:
the chain proves integrity without re-disclosing client data. To prove what a
specific call contained, the operator reveals the payload and anyone can
recompute its hash.

## Canonicalization

All hashing and signing operates on RFC 8785 (JSON Canonicalization Scheme)
bytes: lexicographically sorted keys, no insignificant whitespace, UTF-8,
ECMAScript number formatting. Any compliant JCS implementation produces
identical bytes.

## Signature

- The **body** is the receipt object with the `signature` key removed.
- `signature = base64( Ed25519-sign( private_key, JCS(body) ) )`.
- Verify with the operator's published Ed25519 public key (PEM
  SubjectPublicKeyInfo as produced by `opensteps keygen`).

## Chain linkage

- `receipt_hash = SHA-256( JCS(full receipt, signature included) )`, lowercase hex.
- Receipt *n+1* must carry `prev_hash == receipt_hash(receipt n)`.
- Receipt 0 carries `prev_hash: null`.

Because `prev_hash` covers the signature too, an attacker cannot replace a
receipt (breaks its signature), delete or reorder one (breaks the next
`prev_hash`), or extend someone else's chain without the private key.

## Verification algorithm

For each line, in file order:

1. Parse as JSON; reject the chain if a line is not a JSON object or lacks any
   field listed above.
2. Recompute `JCS(body)` (object minus `signature`) and verify the Ed25519
   signature. Reject on failure.
3. Check `prev_hash` equals the SHA-256 of the previous line's JCS bytes
   (`null` for the first line). Reject on mismatch.
4. Remember this receipt's hash for the next iteration.

A chain with zero receipts is invalid. The final receipt's hash is the **chain
head**; publishing it (Rung 2) commits the operator to the whole history.

What a valid chain proves — and what it doesn't: it proves the recorded calls
happened in this order, signed by the holder of the key, and that nothing
recorded was later altered, dropped, or reordered. It does not prove calls
that bypassed the proxy were recorded, and the keyholder could regenerate an
entire alternative chain from scratch — that is what transparency-log
anchoring (Rung 2) closes off.

## Reference verifier

`src/opensteps/verify.py` (~100 lines, stdlib + Ed25519 + JCS). Run it:

```
opensteps verify receipts.jsonl --pubkey signing.pub
```

Exit codes: `0` valid, `1` invalid, `2` usage error. No network access.
