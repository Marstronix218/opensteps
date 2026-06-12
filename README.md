# OpenSteps

**Independently verifiable receipts for AI agent actions.** Every tool call an
agent makes through OpenSteps becomes a signed, hash-chained Agent Action
Receipt — and an open-source `verify` command lets any third party (an auditor,
a client, a regulator) check the record with no database access and no trust in
the operator or in OpenSteps itself.

Gateways and guardrails log what agents do, but the audit trail is owned by the
party being audited; "tamper-evident" usually means a SOC 2 letter, not
mathematics. OpenSteps is the evidence layer that sits behind or beside any
gateway: the difference between *"our database says"* and *"here is a receipt
you can verify yourself."*

```
 MCP client / agent
        │  tools/call
        ▼
┌───────────────────┐   policy: allow / deny / approve (YAML)
│  opensteps wrap   │──────────────────────────────────────────┐
│  (MCP proxy)      │   every call → signed receipt            │
└────────┬──────────┘   Ed25519 + SHA-256 hash chain (JSONL)   │
         │  allowed calls                                      ▼
         ▼                                          receipts.jsonl ──► opensteps verify
┌───────────────────┐                                        (anyone, offline, no account)
│ your MCP server   │
└───────────────────┘
```

## Quickstart

Requires Python 3.11+.

```bash
git clone https://github.com/Marstronix218/opensteps && cd opensteps
python3 -m venv .venv && .venv/bin/pip install -e .

# 1. generate a signing keypair
.venv/bin/opensteps keygen --out-dir keys

# 2. write a policy (see demo/policy.yaml for a fuller example)
cat > policy.yaml <<'EOF'
version: "0.1"
default: deny
rules:
  - id: reads-ok
    tool: "read_*"
    action: allow
  - id: writes-need-human
    tool: "write_*"
    action: approve
EOF

# 3. wrap your MCP server — wherever your client config used to launch
#    `npx my-mcp-server`, launch this instead:
.venv/bin/opensteps wrap \
  --policy policy.yaml --key keys/signing.key --log receipts.jsonl \
  -- npx my-mcp-server

# 4. anyone with the public key can verify the chain, offline:
.venv/bin/opensteps verify receipts.jsonl --pubkey keys/signing.pub
```

The proxy is a transparent newline-JSON-RPC passthrough that intercepts only
`tools/call`, so it works with any MCP client and server. `deny` blocks the
call before it reaches the server (the agent gets a tool error naming the
rule); `approve` asks a human on the terminal and fails closed on timeout or
when no terminal is available. **Blocked attempts become receipts too.**

## The demo: a prompt-injected bookkeeper

```bash
.venv/bin/pip install -e '.[demo]'
make demo
```

A scripted bookkeeping agent processes invoices through OpenSteps. One invoice
carries a prompt injection directing the agent to wire $45,000 to an attacker.
The agent attempts it; policy blocks it; the blocked attempt becomes receipt
number 4 in the chain; `opensteps verify` proves the whole record; and the demo
then shows that editing or deleting that receipt makes verification fail at
exactly that point. (OWASP Agentic Top 10: ASI01 goal hijack, ASI02 tool
misuse.)

## The receipt format

One JSON object per tool call, hash-chained and signed:

- `request_hash` / `response_hash` — SHA-256 of the RFC 8785 (JCS)
  canonicalized call params and result (hashes, not payloads: no client data
  is re-disclosed).
- `policy` — which rule fired and whether the call was allowed, denied, or
  human-approved.
- `prev_hash` — hash of the previous receipt, signature included: deleting,
  reordering, or rewriting any receipt breaks the chain.
- `signature` — Ed25519 over the canonicalized receipt body.

The full normative spec is [docs/SCHEMA.md](docs/SCHEMA.md) — deliberately
complete enough that a stranger can reimplement the verifier in any language.

## What this proves, honestly

A valid chain proves the recorded calls happened in this order, signed by the
keyholder, with nothing altered, dropped, or reordered afterward. It does not
prove that calls bypassing the proxy were recorded, and a keyholder could
regenerate an entire alternative history. Each rung of the roadmap raises the
attacker's cost:

1. **Signed hash chain** (this repo) — tampering breaks cryptography, not a
   promise.
2. **Transparency-log anchoring** — chain heads published to a public
   append-only log (Sigstore Rekor or equivalent); rewriting history becomes
   publicly visible.
3. **TEE-attested signer** — the signature proves *unmodified, published
   enforcement code* produced the receipt.

The claim is audit-grade, independently verifiable receipts designed to
simplify evidentiary authentication (cf. US FRE 902(13)/902(14)) — not
"court-grade proof." See [docs/OpenSteps_Final.md](docs/OpenSteps_Final.md)
for the full thesis.

## Repository

```
src/opensteps/   proxy, policy engine, receipt signer, offline verifier, CLI
demo/            the prompt-injection launch demo (make demo)
docs/SCHEMA.md   normative receipt format
tests/           unit, tamper-matrix, and end-to-end proxy tests (make test)
legacy/          the superseded v1.0 hosted-gateway prototype (unmaintained)
```

## Development

```bash
make install   # pip install -e '.[dev]' into .venv
make test      # pytest
make demo      # the launch scenario
```

License: Apache-2.0.
