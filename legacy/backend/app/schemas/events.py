from uuid import UUID

from pydantic import BaseModel


class LedgerVerifyRequest(BaseModel):
    run_id: UUID | None = None


class LedgerVerifyResult(BaseModel):
    verified: bool
    checked_events: int
    first_event_id: UUID | None
    last_event_id: UUID | None
    errors: list[str]

