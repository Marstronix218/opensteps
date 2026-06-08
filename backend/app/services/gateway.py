import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.connectors.base import Connector, ConnectorError
from app.connectors.fake_github import FakeGitHubConnector
from app.connectors.fake_slack import FakeSlackConnector
from app.connectors.http_connector import HttpConnector
from app.core.canonical_json import canonical_json, without_fields
from app.core.config import get_settings
from app.core.crypto import verify_signature
from app.core.hashing import hash_json
from app.db.models import Approval, Run
from app.schemas.gateway import ToolCallRequest
from app.services.agents import get_active_agent
from app.services.approvals import validate_approval
from app.services.ledger import EventData, ledger_service
from app.services.policies import policy_engine


class ConnectorRegistry:
    def __init__(self) -> None:
        settings = get_settings()
        self.connectors: dict[str, Connector] = {
            "github": FakeGitHubConnector(),
            "slack": FakeSlackConnector(),
            "http": HttpConnector(settings.http_allowlisted_domains),
        }

    def get(self, tool: str) -> Connector:
        connector = self.connectors.get(tool)
        if connector is None:
            raise ConnectorError(f"No connector registered for tool: {tool}")
        return connector


@dataclass(frozen=True)
class GatewayResult:
    status_code: int
    body: dict[str, Any]


class GatewayService:
    def __init__(self, registry: ConnectorRegistry | None = None) -> None:
        self.registry = registry or ConnectorRegistry()

    def execute(
        self, db: Session, tenant_id: uuid.UUID, request: ToolCallRequest
    ) -> GatewayResult:
        agent = get_active_agent(db, tenant_id, request.agent_id)
        if agent is None:
            return GatewayResult(404, {"status": "error", "detail": "Active agent not found"})
        run = db.get(Run, request.run_id)
        if run is None or run.tenant_id != tenant_id:
            return GatewayResult(404, {"status": "error", "detail": "Run not found"})

        request_body = request.model_dump(mode="json")
        signed_payload = canonical_json(without_fields(request_body, "signature"))
        if not verify_signature(agent.public_key, signed_payload, request.signature):
            return GatewayResult(401, {"status": "error", "detail": "Invalid agent signature"})

        input_hash = hash_json(request.input)
        common = {
            "tenant_id": tenant_id,
            "run_id": request.run_id,
            "agent_id": request.agent_id,
            "tool": request.tool,
            "action": request.action,
            "resource": request.resource,
            "input_hash": input_hash,
        }
        received = ledger_service.append(
            db,
            EventData(
                **common,
                event_type="agent.request_received",
                signature=request.signature,
            ),
        )

        decision = policy_engine.evaluate(
            db,
            tenant_id=tenant_id,
            agent=agent,
            tool=request.tool,
            action=request.action,
            resource=request.resource,
        )
        evaluated = ledger_service.append(
            db,
            EventData(
                **common,
                event_type="policy.evaluated",
                parent_event_id=received.id,
                policy_decision=decision.decision,
            ),
        )
        if decision.decision == "denied":
            ledger_service.append(
                db,
                EventData(
                    **common,
                    event_type="tool_call.failed",
                    parent_event_id=evaluated.id,
                    policy_decision="denied",
                ),
            )
            return GatewayResult(403, {"status": "denied", "detail": "Policy denied action"})

        scope = {
            "agent_id": str(request.agent_id),
            "tool": request.tool,
            "action": request.action,
            "resource": request.resource,
            "input_hash": input_hash,
        }
        approval = None
        if decision.decision == "approval_required":
            if request.approval_id is None:
                approval_event = ledger_service.append(
                    db,
                    EventData(
                        **common,
                        event_type="approval.required",
                        parent_event_id=evaluated.id,
                        policy_decision="approval_required",
                    ),
                )
                approval = Approval(
                    tenant_id=tenant_id,
                    run_id=request.run_id,
                    requested_event_id=approval_event.id,
                    status="pending",
                    scope_json=scope,
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(seconds=get_settings().approval_ttl_seconds),
                )
                db.add(approval)
                db.flush()
                return GatewayResult(
                    202,
                    {
                        "status": "approval_required",
                        "approval_id": str(approval.id),
                        "detail": "Human approval is required before execution",
                    },
                )
            approval, error = validate_approval(
                db,
                approval_id=request.approval_id,
                tenant_id=tenant_id,
                run_id=request.run_id,
                scope=scope,
            )
            if error:
                ledger_service.append(
                    db,
                    EventData(
                        **common,
                        event_type="tool_call.failed",
                        parent_event_id=evaluated.id,
                        policy_decision="approval_required",
                        approval_id=request.approval_id,
                    ),
                )
                return GatewayResult(403, {"status": "denied", "detail": error})

        requested = ledger_service.append(
            db,
            EventData(
                **common,
                event_type="tool_call.requested",
                parent_event_id=evaluated.id,
                policy_decision=decision.decision,
                approval_id=approval.id if approval else None,
            ),
        )
        try:
            connector = self.registry.get(request.tool)
            output = connector.execute(request.action, request.resource, request.input)
            output_hash = hash_json(output)
            ledger_service.append(
                db,
                EventData(
                    **common,
                    event_type="tool_call.completed",
                    parent_event_id=requested.id,
                    output_hash=output_hash,
                    policy_decision=decision.decision,
                    approval_id=approval.id if approval else None,
                ),
            )
            return GatewayResult(200, {"status": "completed", "result": output})
        except Exception as exc:
            ledger_service.append(
                db,
                EventData(
                    **common,
                    event_type="tool_call.failed",
                    parent_event_id=requested.id,
                    policy_decision=decision.decision,
                    approval_id=approval.id if approval else None,
                ),
            )
            detail = str(exc) if isinstance(exc, ConnectorError) else "Connector execution failed"
            return GatewayResult(502, {"status": "failed", "detail": detail})

