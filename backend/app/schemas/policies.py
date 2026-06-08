from uuid import UUID

from pydantic import BaseModel


class PolicyCreate(BaseModel):
    name: str
    policy_yaml: str


class PolicyEvaluate(BaseModel):
    agent_id: UUID
    tool: str
    action: str
    resource: str


class PolicyDecisionOut(BaseModel):
    decision: str
    matched_rule: dict | None = None

