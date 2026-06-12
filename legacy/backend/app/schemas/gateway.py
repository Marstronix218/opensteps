from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    run_id: UUID
    agent_id: UUID
    tool: str
    action: str
    resource: str
    input: dict[str, Any] = Field(default_factory=dict)
    approval_id: UUID | None = None
    signature: str


class ToolCallResult(BaseModel):
    status: str
    result: dict[str, Any] | None = None
    approval_id: UUID | None = None
    detail: str | None = None

