from uuid import UUID

from pydantic import BaseModel


class RunCreate(BaseModel):
    initiated_by_user_id: UUID | None = None
    root_agent_id: UUID | None = None

