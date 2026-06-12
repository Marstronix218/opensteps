# OpenSteps

OpenSteps is an enforceable authorization gateway and tamper-evident audit ledger for AI-agent
tool calls. Agents sign requests and call OpenSteps instead of tools directly. OpenSteps verifies
identity, evaluates policy, gates risky actions on human approval, invokes a controlled connector,
and records each decision and result in a hash-linked event chain.

The product promise is: **every AI-agent action is authorized, attributable, and tamper-evident.**

OpenSteps does not inspect or prove an agent's reasoning, prevent every malicious action, secure
tools that bypass the gateway, or replace sandboxing and least privilege. It is not a chatbot,
cryptocurrency, token system, or blockchain.

## Architecture

```text
 signed agent request
          |
          v
 +-------------------+     +------------------+
 | OpenSteps Gateway |---->| Agent public key |
 +---------+---------+     +------------------+
           |
           v
 +-------------------+   deny    +-----------------------+
 | YAML Policy Engine|---------->| blocked before tool   |
 +---------+---------+           +-----------------------+
           | allow / approval_required
           v
 +-------------------+           +-----------------------+
 | Human Approval    |---------->| GitHub/Slack/HTTP     |
 +---------+---------+  approved +-----------------------+
           |                           |
           +-------------+-------------+
                         v
              +---------------------+
              | Append-only events  |
              | SHA-256 hash chain  |
              +----------+----------+
                         v
              +---------------------+
              | Merkle checkpoint   |
              | Ed25519 signature   |
              +----------+----------+
                         v
              +---------------------+
              | Audit dashboard     |
              +---------------------+
```

## Local setup

Requirements: Docker with Compose and `make`.

```bash
cp .env.example .env
make up
```

`make up` builds the stack and applies Alembic migrations. The backend also migrates on container
startup, so plain `docker compose up --build` is sufficient. Services:

- Dashboard: http://localhost:3000
- API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs
- PostgreSQL: internal Compose network only

Use a newly generated `SERVICE_PRIVATE_KEY` outside local development. The example key is public
test material and must never be used in a deployed environment.

## Commands

```bash
make up       # build and start backend, frontend, PostgreSQL
make down     # stop services
make migrate  # apply Alembic migrations
make test     # run backend tests
make seed     # create tenant, user, agent, and policy
make demo     # execute the full signed authorization workflow
```

`make demo` creates a tenant, approver, Ed25519 agent, policy, and run. It executes an allowed fake
pull request, pauses a merge for approval, retries after approval, proves an AWS deletion is denied
before connector execution, completes the run, signs a checkpoint, verifies the ledger, and prints
dashboard URLs.

For local tests without Docker:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e 'backend[dev]'
cd backend && ../.venv/bin/pytest
```

## API examples

Create a tenant and agent:

```bash
curl -X POST http://localhost:8000/tenants \
  -H 'content-type: application/json' \
  -d '{"name":"Example"}'

curl -X POST http://localhost:8000/tenants/$TENANT_ID/agents \
  -H 'content-type: application/json' \
  -d '{"name":"code-agent","public_key":"BASE64_ED25519_PUBLIC_KEY"}'
```

Verify a tenant or run ledger:

```bash
curl -X POST http://localhost:8000/tenants/$TENANT_ID/ledger/verify \
  -H 'content-type: application/json' \
  -d '{"run_id":"OPTIONAL_RUN_UUID"}'
```

The signed gateway body is:

```json
{
  "run_id": "uuid",
  "agent_id": "uuid",
  "tool": "github",
  "action": "create_pull_request",
  "resource": "repo:example/app",
  "input": {"title": "Fix bug", "branch": "fix-bug"},
  "approval_id": null,
  "signature": "base64 Ed25519 signature"
}
```

See `examples/python_agent_client/client.py` for canonicalization and signing code.

## Security design

### Agent signatures

Each agent has an Ed25519 public key. The client removes `signature`, serializes the remaining
request as deterministic JSON (sorted keys, compact separators, UTF-8), and signs those bytes.
The gateway verifies the signature before treating the request as attributable. Invalid signatures
are rejected with HTTP 401.

### Event hashes

OpenSteps stores hashes of tool inputs and outputs, not raw payloads. Each event hash is SHA-256
over canonical event fields plus `previous_hash`. Event IDs and UTC timestamps are included.
Events have no update or delete API, and ORM update/delete hooks reject accidental application-level
mutation.

### Ledger verification

Verification reads the tenant chain in order, recomputes every event hash, and confirms each
`previous_hash` points to the preceding event. A failure reports the exact event and expected value.
A run-scoped request reports the run's checked-event count while validating the full tenant chain
that anchors it.

This detects mutation after the fact. A database administrator can still rewrite an entire chain;
exported signed checkpoints are the planned external anchor for detecting that stronger attack.

### Approvals

A policy can return `approval_required`. OpenSteps records the requirement and creates a pending,
expiring approval whose scope binds:

- agent ID
- tool
- action
- resource
- input hash

The connector is not called. An authorized user approves or rejects the request. The agent then
re-signs and retries with the approval ID. OpenSteps rejects expired, rejected, cross-tenant,
cross-run, or scope-mismatched approvals. Supplying an approval to a different action does not
bypass policy.

### Checkpoints

A checkpoint covers all new event hashes since the previous checkpoint. Leaves are folded into a
deterministic SHA-256 Merkle root (duplicating an odd final leaf), then the checkpoint metadata is
signed by the service Ed25519 key. A `checkpoint.created` event is appended after the boundary.

### HTTP connector

The HTTP connector requires HTTPS, exact hostname allowlisting, a bounded method set, a ten-second
timeout, and disabled redirects. Response bodies are not persisted. Production deployments should
also enforce egress controls at the network layer.

## Threat model

OpenSteps protects against silent log tampering after the fact by making mutations break the event
hash chain. It supports attribution through verified agent signatures and enforcement through
gateway policies and approval gates.

OpenSteps does **not** prove the AI agent's reasoning is correct. It does not protect any action that
bypasses the gateway and does not eliminate the need for sandboxing, least privilege, secret
isolation, connector-specific permissions, network controls, and independent monitoring. A
compromised service signing key or database plus signing service requires key rotation and external
checkpoint storage to contain. OpenSteps is not a blockchain.

## Repository

```text
backend/    FastAPI, SQLAlchemy, Alembic, policy and ledger services, tests
frontend/   Next.js TypeScript audit dashboard
examples/   signed Python agent client and demo workflow
```

The fake GitHub and Slack connectors never contact external services. The HTTP connector is the only
MVP connector that performs outbound I/O.

## Roadmap

- Real GitHub integration
- MCP proxy
- Open Policy Agent integration
- Customer-owned S3 checkpoint export
- Cloud KMS/HSM support
- SOC 2 evidence export
- SIEM integration
- Real-time anomaly detection

