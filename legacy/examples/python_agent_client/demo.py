import argparse
import json
import os
from typing import Any

import httpx

from app.core.crypto import generate_keypair
from examples.python_agent_client.client import OpenStepsAgentClient

POLICY = """\
default: deny

rules:
  - effect: allow
    agent: code-agent
    tool: github
    actions:
      - create_pull_request
    resources:
      - repo:example/app

  - effect: approval_required
    agent: code-agent
    tool: github
    actions:
      - merge_pull_request
    resources:
      - repo:example/app

  - effect: deny
    agent: code-agent
    tool: aws
    actions:
      - delete_instance
    resources:
      - "*"
"""


def post(base_url: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
    response = httpx.post(f"{base_url}{path}", json=body, timeout=15)
    response.raise_for_status()
    return response.json()


def seed(base_url: str) -> dict[str, str]:
    private_key, public_key = generate_keypair()
    tenant = post(base_url, "/tenants", {"name": "OpenSteps Demo"})
    user = post(
        base_url,
        f"/tenants/{tenant['id']}/users",
        {"email": "approver@opensteps.local", "name": "Demo Approver", "role": "admin"},
    )
    agent = post(
        base_url,
        f"/tenants/{tenant['id']}/agents",
        {"name": "code-agent", "public_key": public_key},
    )
    post(
        base_url,
        f"/tenants/{tenant['id']}/policies",
        {"name": "Demo agent policy", "policy_yaml": POLICY},
    )
    return {
        "tenant_id": tenant["id"],
        "user_id": user["id"],
        "agent_id": agent["id"],
        "private_key": private_key,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OpenSteps signed-agent demo")
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()
    base_url = os.getenv("OPENSTEPS_API_URL", "http://localhost:8000").rstrip("/")
    setup = seed(base_url)
    print("Seeded demo tenant:")
    print(json.dumps({key: value for key, value in setup.items() if key != "private_key"}, indent=2))
    if args.seed_only:
        print(f"\nDashboard: http://localhost:3000/tenants/{setup['tenant_id']}/runs")
        return

    run = post(
        base_url,
        f"/tenants/{setup['tenant_id']}/runs",
        {"root_agent_id": setup["agent_id"], "initiated_by_user_id": setup["user_id"]},
    )
    client = OpenStepsAgentClient(
        base_url, setup["tenant_id"], setup["agent_id"], setup["private_key"]
    )
    client.tool_call(
        run_id=run["id"],
        tool="github",
        action="create_pull_request",
        resource="repo:example/app",
        input_data={"title": "Fix authorization bug", "branch": "fix/authz"},
    )
    approval_response = client.tool_call(
        run_id=run["id"],
        tool="github",
        action="merge_pull_request",
        resource="repo:example/app",
        input_data={"pull_request": 42},
    )
    approval_id = approval_response.json()["approval_id"]
    approval = post(
        base_url,
        f"/tenants/{setup['tenant_id']}/approvals/{approval_id}/approve",
        {"user_id": setup["user_id"]},
    )
    print(f"\n[approval] {approval['status']} by {approval['approved_by']}")
    client.tool_call(
        run_id=run["id"],
        tool="github",
        action="merge_pull_request",
        resource="repo:example/app",
        input_data={"pull_request": 42},
        approval_id=approval_id,
    )
    denied = client.tool_call(
        run_id=run["id"],
        tool="aws",
        action="delete_instance",
        resource="instance:production",
        input_data={"instance_id": "i-production"},
    )
    assert denied.status_code == 403
    print("[proof] denied action was blocked before connector execution")

    post(base_url, f"/tenants/{setup['tenant_id']}/runs/{run['id']}/complete", {})
    checkpoint = post(base_url, f"/tenants/{setup['tenant_id']}/checkpoints", {})
    print(f"\n[checkpoint] {checkpoint['event_count']} events -> {checkpoint['merkle_root']}")
    verification = post(base_url, f"/tenants/{setup['tenant_id']}/ledger/verify", {})
    print("\n[ledger verification]")
    print(json.dumps(verification, indent=2))
    assert verification["verified"] is True

    print("\nDashboard URLs")
    print(f"  Runs:        http://localhost:3000/tenants/{setup['tenant_id']}/runs")
    print(f"  Run detail:  http://localhost:3000/tenants/{setup['tenant_id']}/runs/{run['id']}")
    print(f"  Approvals:   http://localhost:3000/tenants/{setup['tenant_id']}/approvals")
    print(f"  Checkpoints: http://localhost:3000/tenants/{setup['tenant_id']}/checkpoints")


if __name__ == "__main__":
    main()
