from uuid import UUID

from pydantic import BaseModel


class ApprovalDecision(BaseModel):
    user_id: UUID

