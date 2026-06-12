from typing import Any

from fastapi.testclient import TestClient

from app.api import gateway as gateway_api
from app.connectors.base import Connector
from app.services.gateway import ConnectorRegistry, GatewayService
from app.tests.helpers import setup_demo, signed_request


class SpyConnector(Connector):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def execute(self, action: str, resource: str, input_data: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((action, resource, input_data))
        return {"ok": True, "action": action}


def install_spy() -> SpyConnector:
    spy = SpyConnector()
    registry = ConnectorRegistry()
    registry.connectors["github"] = spy
    registry.connectors["aws"] = spy
    gateway_api.gateway_service = GatewayService(registry)
    return spy


def test_invalid_signature_is_rejected(client: TestClient) -> None:
    setup = setup_demo(client)
    body = signed_request(setup, tool="github", action="create_pull_request")
    body["signature"] = "not-a-signature"
    response = client.post(
        f"/tenants/{setup['tenant_id']}/gateway/tool-call", json=body
    )
    assert response.status_code == 401


def test_allowed_fake_github_action_executes(client: TestClient) -> None:
    setup = setup_demo(client)
    body = signed_request(
        setup,
        tool="github",
        action="create_pull_request",
        input_data={"title": "Fix bug", "branch": "fix-bug"},
    )
    response = client.post(
        f"/tenants/{setup['tenant_id']}/gateway/tool-call", json=body
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["result"]["sandbox"] is True


def test_denied_action_never_reaches_connector(client: TestClient) -> None:
    spy = install_spy()
    setup = setup_demo(client)
    body = signed_request(
        setup, tool="aws", action="delete_instance", resource="instance:prod-1"
    )
    response = client.post(
        f"/tenants/{setup['tenant_id']}/gateway/tool-call", json=body
    )
    assert response.status_code == 403
    assert spy.calls == []


def test_approval_required_does_not_execute_and_matching_retry_does(
    client: TestClient,
) -> None:
    spy = install_spy()
    setup = setup_demo(client)
    input_data = {"pull_request": 42}
    initial = signed_request(
        setup, tool="github", action="merge_pull_request", input_data=input_data
    )
    response = client.post(
        f"/tenants/{setup['tenant_id']}/gateway/tool-call", json=initial
    )
    assert response.status_code == 202
    assert spy.calls == []
    approval_id = response.json()["approval_id"]

    approved = client.post(
        f"/tenants/{setup['tenant_id']}/approvals/{approval_id}/approve",
        json={"user_id": setup["user_id"]},
    )
    assert approved.status_code == 200
    retry = signed_request(
        setup,
        tool="github",
        action="merge_pull_request",
        input_data=input_data,
        approval_id=approval_id,
    )
    completed = client.post(
        f"/tenants/{setup['tenant_id']}/gateway/tool-call", json=retry
    )
    assert completed.status_code == 200
    assert len(spy.calls) == 1


def test_approval_cannot_be_reused_for_different_scope(client: TestClient) -> None:
    spy = install_spy()
    setup = setup_demo(client)
    initial = signed_request(
        setup,
        tool="github",
        action="merge_pull_request",
        input_data={"pull_request": 42},
    )
    approval_id = client.post(
        f"/tenants/{setup['tenant_id']}/gateway/tool-call", json=initial
    ).json()["approval_id"]
    client.post(
        f"/tenants/{setup['tenant_id']}/approvals/{approval_id}/approve",
        json={"user_id": setup["user_id"]},
    )
    mismatched = signed_request(
        setup,
        tool="github",
        action="merge_pull_request",
        input_data={"pull_request": 99},
        approval_id=approval_id,
    )
    response = client.post(
        f"/tenants/{setup['tenant_id']}/gateway/tool-call", json=mismatched
    )
    assert response.status_code == 403
    assert "scope" in response.json()["detail"].lower()
    assert spy.calls == []

    different_action = signed_request(
        setup,
        tool="github",
        action="create_pull_request",
        input_data={"pull_request": 42},
        approval_id=approval_id,
    )
    response = client.post(
        f"/tenants/{setup['tenant_id']}/gateway/tool-call", json=different_action
    )
    assert response.status_code == 403
    assert spy.calls == []
