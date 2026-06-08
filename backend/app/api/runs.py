import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Event, Run, Tenant
from app.db.session import get_db
from app.schemas.common import RunDetail, RunOut
from app.schemas.runs import RunCreate
from app.services.ledger import EventData, ledger_service

router = APIRouter(prefix="/tenants/{tenant_id}/runs", tags=["runs"])


@router.post("", response_model=RunOut, status_code=201)
def create_run(
    tenant_id: uuid.UUID, payload: RunCreate, db: Session = Depends(get_db)
) -> Run:
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(404, "Tenant not found")
    run = Run(tenant_id=tenant_id, **payload.model_dump())
    db.add(run)
    db.flush()
    ledger_service.append(
        db,
        EventData(
            tenant_id=tenant_id,
            run_id=run.id,
            event_type="run.started",
            agent_id=run.root_agent_id,
            user_id=run.initiated_by_user_id,
        ),
    )
    db.commit()
    return run


@router.get("", response_model=list[RunOut])
def list_runs(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Run]:
    return list(
        db.scalars(
            select(Run).where(Run.tenant_id == tenant_id).order_by(Run.started_at.desc())
        )
    )


@router.get("/{run_id}", response_model=RunDetail)
def get_run(
    tenant_id: uuid.UUID, run_id: uuid.UUID, db: Session = Depends(get_db)
) -> dict:
    run = db.get(Run, run_id)
    if run is None or run.tenant_id != tenant_id:
        raise HTTPException(404, "Run not found")
    events = list(
        db.scalars(
            select(Event)
            .where(Event.tenant_id == tenant_id, Event.run_id == run_id)
            .order_by(Event.timestamp.asc(), Event.id.asc())
        )
    )
    return {**RunOut.model_validate(run).model_dump(), "events": events}

