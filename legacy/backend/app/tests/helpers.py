from typing import Any

from fastapi.testclient import TestClient

from app.core.canonical_json import canonical_json
from app.core.crypto import generate_keypair, sign_payload

POLICY = """\
default: deny
rules:
  - effect: allow
    agent: code-agent
    tool: github
    actions: [create_pull_request]
    resources: [repo:example/app]
  - effect: approval_required
    agent: code-agent
    tool: github
    actions: [merge_pull_request]
    resources: [repo:example/app]
  - effect: deny
    agent: code-agent
    tool: aws
    actions: [delete_instance]
    resources: ["*"]
"""


def setup_demo(client: TestClient) -> dict[str, str]:
    tenant = client.post("/tenants", json={"name": "Demo"}).json()
    user = client.post(
        f"/tenants/{tenant['id']}/users",
        json={"email": "approver@example.com", "name": "Demo Approver", "role": "admin"},
    ).json()
    private_key, public_key = generate_keypair()
    agent = client.post(
        f"/tenants/{tenant['id']}/agents",
        json={"name": "code-agent", "public_key": public_key},
    ).json()
    policy_response = client.post(
        f"/tenants/{tenant['id']}/policies",
        json={"name": "Demo policy", "policy_yaml": POLICY},
    )
    assert policy_response.status_code == 201, policy_response.text
    run = client.post(
        f"/tenants/{tenant['id']}/runs",
        json={"root_agent_id": agent["id"], "initiated_by_user_id": user["id"]},
    ).json()
    return {
        "tenant_id": tenant["id"],
        "user_id": user["id"],
        "agent_id": agent["id"],
        "run_id": run["id"],
        "private_key": private_key,
        "public_key": public_key,
    }


def signed_request(
    setup: dict[str, str],
    *,
    tool: str,
    action: str,
    resource: str = "repo:example/app",
    input_data: dict[str, Any] | None = None,
    approval_id: str | None = None,
) -> dict[str, Any]:
    body = {
        "run_id": setup["run_id"],
        "agent_id": setup["agent_id"],
        "tool": tool,
        "action": action,
        "resource": resource,
        "input": input_data or {},
        "approval_id": approval_id,
    }
    body["signature"] = sign_payload(setup["private_key"], canonical_json(body))
    return body

