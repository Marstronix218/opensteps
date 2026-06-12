from typing import Any
from urllib.parse import urlparse

import httpx

from app.connectors.base import Connector, ConnectorError


class HttpConnector(Connector):
    def __init__(self, allowlisted_domains: list[str]) -> None:
        self.allowlisted_domains = set(allowlisted_domains)

    def execute(self, action: str, resource: str, input_data: dict[str, Any]) -> dict[str, Any]:
        if action != "request":
            raise ConnectorError(f"Unsupported HTTP action: {action}")
        url = str(input_data.get("url", ""))
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in self.allowlisted_domains:
            raise ConnectorError("URL must use HTTPS and target an allowlisted domain")
        method = str(input_data.get("method", "GET")).upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ConnectorError("Unsupported HTTP method")
        with httpx.Client(follow_redirects=False, timeout=10) as client:
            response = client.request(
                method,
                url,
                headers=input_data.get("headers"),
                json=input_data.get("json"),
            )
        return {
            "status_code": response.status_code,
            "headers": {"content-type": response.headers.get("content-type")},
            "body_hash_only": True,
        }

