import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Event
from app.db.session import get_db
from app.schemas.common import EventOut
from app.schemas.events import LedgerVerifyRequest, LedgerVerifyResult
from app.services.ledger import ledger_service

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["events"])


@router.get("/events", response_model=list[EventOut])
def list_events(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(Event.tenant_id == tenant_id)
            .order_by(Event.timestamp.asc(), Event.id.asc())
        )
    )


@router.get("/runs/{run_id}/events", response_model=list[EventOut])
def list_run_events(
    tenant_id: uuid.UUID, run_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[Event]:
    return list(
        db.scalars(
            select(Event)
            .where(Event.tenant_id == tenant_id, Event.run_id == run_id)
            .order_by(Event.timestamp.asc(), Event.id.asc())
        )
    )


@router.post("/ledger/verify", response_model=LedgerVerifyResult)
def verify_ledger(
    tenant_id: uuid.UUID,
    payload: LedgerVerifyRequest,
    db: Session = Depends(get_db),
) -> dict:
    return ledger_service.verify(db, tenant_id, payload.run_id)

