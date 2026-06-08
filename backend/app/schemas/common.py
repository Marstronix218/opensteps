from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TenantOut(ORMModel):
    id: UUID
    name: str
    created_at: datetime


class UserOut(ORMModel):
    id: UUID
    tenant_id: UUID
    email: str
    name: str
    role: str
    created_at: datetime


class AgentOut(ORMModel):
    id: UUID
    tenant_id: UUID
    name: str
    public_key: str
    status: str
    created_at: datetime


class EventOut(ORMModel):
    id: UUID
    tenant_id: UUID
    run_id: UUID
    parent_event_id: UUID | None
    event_type: str
    agent_id: UUID | None
    user_id: UUID | None
    tool: str | None
    action: str | None
    resource: str | None
    input_hash: str | None
    output_hash: str | None
    policy_decision: str | None
    approval_id: UUID | None
    previous_hash: str | None
    event_hash: str
    signature: str | None
    timestamp: datetime


class RunOut(ORMModel):
    id: UUID
    tenant_id: UUID
    initiated_by_user_id: UUID | None
    root_agent_id: UUID | None
    status: str
    started_at: datetime
    ended_at: datetime | None


class RunDetail(RunOut):
    events: list[EventOut]


class PolicyOut(ORMModel):
    id: UUID
    tenant_id: UUID
    name: str
    policy_yaml: str
    status: str
    created_at: datetime


class ApprovalOut(ORMModel):
    id: UUID
    tenant_id: UUID
    run_id: UUID
    requested_event_id: UUID
    approved_by: UUID | None
    status: str
    scope_json: dict
    expires_at: datetime
    created_at: datetime
    decided_at: datetime | None


class CheckpointOut(ORMModel):
    id: UUID
    tenant_id: UUID
    from_event_id: UUID
    to_event_id: UUID
    merkle_root: str
    event_count: int
    signature: str
    created_at: datetime

