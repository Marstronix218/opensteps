import uuid
from datetime import datetime, timezone
from typing import Any

from app.connectors.base import Connector, ConnectorError


class FakeSlackConnector(Connector):
    def execute(self, action: str, resource: str, input_data: dict[str, Any]) -> dict[str, Any]:
        if action != "send_message":
            raise ConnectorError(f"Unsupported fake Slack action: {action}")
        return {
            "id": str(uuid.uuid4()),
            "channel": resource,
            "text": input_data.get("text", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sandbox": True,
        }

