import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Checkpoint
from app.db.session import get_db
from app.schemas.checkpoints import CheckpointCreate
from app.schemas.common import CheckpointOut
from app.services.checkpoints import checkpoint_service

router = APIRouter(prefix="/tenants/{tenant_id}/checkpoints", tags=["checkpoints"])


@router.post("", response_model=CheckpointOut, status_code=201)
def create_checkpoint(
    tenant_id: uuid.UUID,
    _: CheckpointCreate,
    db: Session = Depends(get_db),
) -> Checkpoint:
    try:
        checkpoint = checkpoint_service.create(db, tenant_id)
        db.commit()
        return checkpoint
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.get("", response_model=list[CheckpointOut])
def list_checkpoints(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Checkpoint]:
    return list(
        db.scalars(
            select(Checkpoint)
            .where(Checkpoint.tenant_id == tenant_id)
            .order_by(Checkpoint.created_at.desc())
        )
    )

