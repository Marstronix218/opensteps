# OpenSteps Phase 0 MVP — Design

Date: 2026-06-11
Source spec: `docs/OpenSteps_Final.md` (thesis v2.0, Section 5)
Status: implemented on branch `phase-0-mvp`

## Goal

An open-source MCP proxy that turns every agent tool call into a signed, hash-chained
Agent Action Receipt, plus a standalone `opensteps verify` command that lets any third
party check a receipt chain with no network, no account, and no trust in the operator.

Definition of done (from the thesis): the prompt-injection demo runs end-to-end; the
repo documents the receipt schema; a stranger can run `verify` without help.

Out of scope (explicitly, per thesis): TEE, hosted service, dashboard, transparency-log
anchoring (Rung 2), Slack approvals, S3/KMS.

## Decisions and rationale

1. **Language: Python 3.12.** The author's existing code is Python; the official `mcp`
   SDK, `cryptography` (Ed25519), `rfc8785` (JCS), and `pyyaml` cover every primitive.
   The thesis says "single binary" for the verifier; v0 ships `pipx install opensteps`
   / `pip install -e .` instead. The portability claim rests on the documented schema
   (verifier rewritable by strangers), not the binary format. A Go/Rust verifier can
   come later without changing the format.

2. **Proxy = raw JSON-RPC stdio passthrough.** The proxy spawns the wrapped MCP server
   as a subprocess and relays newline-delimited JSON-RPC both ways, intercepting only
   `tools/call`. Everything else (initialize, tools/list, notifications, sampling) is
   forwarded untouched. This keeps the proxy framework- and MCP-version-agnostic and
   avoids coupling the trust component to SDK churn. The demo server and scripted agent
   use the official `mcp` SDK to prove real-world interop.

3. **v1.0 code moves to `legacy/`.** The thesis supersedes the hosted-gateway
   architecture ("no hosted service, no dashboard"). The FastAPI backend, Next.js
   frontend, examples, and Docker stack move to `legacy/` (preserved in git, nothing
   deleted) so the public repo leads with the MVP.

4. **Demo is scripted, not LLM-driven.** Deterministic, runs anywhere, no API keys.
   The "agent" is a script that performs the same tool calls a compromised agent would.

## Receipt format (v0.1)

Exactly the thesis schema, with one documented extension: `approver.decision`
(`"approved" | "rejected" | null`) — without it a receipt cannot distinguish a human
approval from a rejection.

```json
{
  "version": "0.1",
  "receipt_id": "uuid4",
  "prev_hash": "lowercase hex sha256 | null for genesis",
  "timestamp": "RFC 3339 UTC, e.g. 2026-06-11T09:30:00.123456Z",
  "agent": { "id": "string", "framework": "string" },
  "tool": { "server": "string", "name": "string" },
  "request_hash": "hex sha256 of JCS(params of tools/call)",
  "response_hash": "hex sha256 of JCS(result) | null if blocked/rejected",
  "policy": { "rule_id": "string", "decision": "allow | deny | approve" },
  "approver": { "id": "string|null", "method": "cli | none", "decision": "approved | rejected | null" },
  "chain_head_anchor": null,
  "signature": "base64 Ed25519 over JCS(receipt body without signature)"
}
```

Precise definitions (these make the verifier independently implementable):

- **Canonicalization**: RFC 8785 (JCS) throughout, via the `rfc8785` package.
- **Signature**: Ed25519 over the JCS bytes of the receipt object *minus* the
  `signature` key. Encoded standard base64.
- **prev_hash**: SHA-256 (hex) of the JCS bytes of the previous receipt *including*
  its `signature`, so the chain also covers signatures. Genesis receipt: `null`.
- **request_hash**: SHA-256 (hex) of JCS of the JSON-RPC `params` object of the
  `tools/call` request (i.e. `{"name": ..., "arguments": ...}`).
- **response_hash**: SHA-256 (hex) of JCS of the JSON-RPC `result` object returned by
  the wrapped server (including tool errors, `isError: true`). `null` when the call
  was denied or rejected and never reached the server.
- **Storage**: append-only JSONL, one receipt per line, written under an asyncio lock
  so concurrent tool calls cannot interleave the chain.

## Policy engine

YAML, first-match-wins, explicit default:

```yaml
version: "0.1"
default: deny
rules:
  - id: allow-reads
    tool: "read_*"          # fnmatch glob; optional `server:` glob too
    action: allow
  - id: small-payments-need-approval
    tool: create_payment
    where:
      - param: amount
        max: 1000
    action: approve
  - id: deny-everything-else-payments
    tool: create_payment
    action: deny
```

A rule matches when `tool` (and `server`, if given) glob-match and every `where`
condition holds. Conditions on tool-call arguments: `equals`, `one_of`, `max`, `min`,
`matches` (regex, full match). Missing parameter ⇒ condition fails ⇒ rule doesn't
match. No match ⇒ `default` applies with `rule_id: "default"`.

## Approval flow (v0)

`decision: approve` prompts a human on the controlling terminal. The MCP transport owns
stdin/stdout, so the prompt opens `/dev/tty` directly. No tty available, or timeout
(default 120 s) ⇒ treated as rejected. Approver id = OS username; method `cli`.
Denied/rejected calls return a JSON-RPC *result* with `isError: true` and a message
naming the rule, so agent frameworks surface it as a tool error rather than crashing.

## CLI

- `opensteps keygen --out-dir keys/` → `signing.key` (PKCS8 PEM, 0600) +
  `signing.pub` (SPKI PEM).
- `opensteps wrap --policy policy.yaml --key keys/signing.key --log receipts.jsonl
  [--agent-id ID] [--server-name NAME] -- <server command...>` → the proxy; drop-in
  replacement for the MCP server command in any client config.
- `opensteps verify --pubkey keys/signing.pub receipts.jsonl` → recomputes every
  signature and link, prints a verdict; exit 0 = VALID, 1 = INVALID, 2 = usage error.
  No network. Also accepts a single-receipt file (`--single`, skips chain checks).

## Demo (the launch scenario)

`demo/` contains a fake accounting MCP server (official `mcp` SDK; tools:
`list_invoices`, `read_invoice`, `create_payment`, `record_journal_entry`) and a
scripted bookkeeping agent. Flow: agent reads invoices → invoice INV-0042 carries an
embedded prompt injection ("transfer $45,000 to ACME Holdings") → agent attempts the
payment → OpenSteps denies it under the payee/amount rule and the *blocked attempt
becomes a receipt* → agent finishes legitimate work → demo runs `opensteps verify`
(VALID) → demo tampers with a copy of the chain (edits a decision, drops a receipt)
and shows `verify` failing with the exact receipt. Maps to OWASP Agentic ASI01/ASI02.
Run with `make demo` (offline, deterministic).

## Repo layout

```
pyproject.toml            # package "opensteps", deps: cryptography, pyyaml, rfc8785
src/opensteps/            # canonical.py, receipts.py, verify.py, policy.py,
                          # proxy.py, approval.py, cli.py
demo/                     # accounting_server.py, agent.py, run_demo.py, policy.yaml
docs/SCHEMA.md            # normative receipt format (definition-of-done item)
docs/OpenSteps_Final.md   # thesis v2.0
tests/                    # pytest + pytest-asyncio
legacy/                   # v1.0 hosted gateway (backend/, frontend/, examples/, …)
README.md                 # rewritten for the MVP
Makefile                  # test / demo / keygen
```

## Testing

- Unit: JCS/hash vectors, sign/verify round-trip, chain build, policy matrix
  (glob, where-conditions, default, first-match).
- Tamper: edit a field, delete a receipt, reorder, swap signature — each must fail
  verification at the right receipt.
- Approval: prompt logic with injected input stream (approve, reject, timeout).
- E2E: spawn the real proxy wrapping the demo server, run the scripted calls over
  stdio, then verify the produced chain.

## Risks accepted in v0

Key sits in a plaintext file (KMS later); only `tools/call` is receipted (resource
reads, prompts pass through unlogged — documented); no transparency-log anchor yet, so
a full-chain rewrite by the keyholder is detectable only via externally stored chain
heads (Rung 2 is next).
