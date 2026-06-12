import uuid
from typing import Any

from app.connectors.base import Connector, ConnectorError


class FakeGitHubConnector(Connector):
    def execute(self, action: str, resource: str, input_data: dict[str, Any]) -> dict[str, Any]:
        if action == "create_pull_request":
            return {
                "id": str(uuid.uuid4()),
                "number": 42,
                "state": "open",
                "title": input_data.get("title", "Untitled"),
                "resource": resource,
                "sandbox": True,
            }
        if action == "merge_pull_request":
            return {
                "merged": True,
                "merge_sha": uuid.uuid4().hex,
                "resource": resource,
                "sandbox": True,
            }
        raise ConnectorError(f"Unsupported fake GitHub action: {action}")

