import json
from pathlib import Path
from typing import Any

import httpx

from app.core.canonical_json import canonical_json
from app.core.crypto import generate_keypair, public_key_from_private, sign_payload


class OpenStepsAgentClient:
    def __init__(
        self,
        base_url: str,
        tenant_id: str,
        agent_id: str,
        private_key: str,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.private_key = private_key

    @staticmethod
    def generate_or_load_keypair(path: Path) -> tuple[str, str]:
        if path.exists():
            private_key = path.read_text().strip()
            return private_key, public_key_from_private(private_key)
        private_key, public_key = generate_keypair()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(private_key)
        path.chmod(0o600)
        return private_key, public_key

    def tool_call(
        self,
        *,
        run_id: str,
        tool: str,
        action: str,
        resource: str,
        input_data: dict[str, Any],
        approval_id: str | None = None,
    ) -> httpx.Response:
        body = {
            "run_id": run_id,
            "agent_id": self.agent_id,
            "tool": tool,
            "action": action,
            "resource": resource,
            "input": input_data,
            "approval_id": approval_id,
        }
        body["signature"] = sign_payload(self.private_key, canonical_json(body))
        response = httpx.post(
            f"{self.base_url}/tenants/{self.tenant_id}/gateway/tool-call",
            json=body,
            timeout=15,
        )
        self.print_response(f"{tool}.{action}", response)
        return response

    @staticmethod
    def print_response(label: str, response: httpx.Response) -> None:
        print(f"\n[{label}] HTTP {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2))
        except ValueError:
            print(response.text)

