import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Approval, Event, User
from app.db.session import get_db
from app.schemas.approvals import ApprovalDecision
from app.schemas.common import ApprovalOut
from app.services.approvals import utc_aware
from app.services.ledger import EventData, ledger_service

router = APIRouter(prefix="/tenants/{tenant_id}/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
def list_approvals(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Approval]:
    approvals = list(
        db.scalars(
            select(Approval)
            .where(Approval.tenant_id == tenant_id)
            .order_by(Approval.created_at.desc())
        )
    )
    now = datetime.now(timezone.utc)
    changed = False
    for approval in approvals:
        if approval.status == "pending" and utc_aware(approval.expires_at) <= now:
            approval.status = "expired"
            changed = True
    if changed:
        db.commit()
    return approvals


def decide(
    db: Session,
    tenant_id: uuid.UUID,
    approval_id: uuid.UUID,
    payload: ApprovalDecision,
    status: str,
) -> Approval:
    approval = db.get(Approval, approval_id)
    if approval is None or approval.tenant_id != tenant_id:
        raise HTTPException(404, "Approval not found")
    user = db.get(User, payload.user_id)
    if user is None or user.tenant_id != tenant_id:
        raise HTTPException(404, "Approver not found")
    if user.role not in {"admin", "approver"}:
        raise HTTPException(403, "User is not permitted to approve actions")
    if approval.status != "pending":
        raise HTTPException(409, f"Approval is already {approval.status}")
    if utc_aware(approval.expires_at) <= datetime.now(timezone.utc):
        approval.status = "expired"
        db.commit()
        raise HTTPException(409, "Approval has expired")

    requested = db.get(Event, approval.requested_event_id)
    approval.status = status
    approval.approved_by = user.id
    approval.decided_at = datetime.now(timezone.utc)
    scope = approval.scope_json
    ledger_service.append(
        db,
        EventData(
            tenant_id=tenant_id,
            run_id=approval.run_id,
            event_type="approval.granted" if status == "approved" else "approval.rejected",
            parent_event_id=requested.id if requested else None,
            agent_id=uuid.UUID(scope["agent_id"]),
            user_id=user.id,
            tool=scope["tool"],
            action=scope["action"],
            resource=scope["resource"],
            input_hash=scope["input_hash"],
            approval_id=approval.id,
        ),
    )
    db.commit()
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
def approve(
    tenant_id: uuid.UUID,
    approval_id: uuid.UUID,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
) -> Approval:
    return decide(db, tenant_id, approval_id, payload, "approved")


@router.post("/{approval_id}/reject", response_model=ApprovalOut)
def reject(
    tenant_id: uuid.UUID,
    approval_id: uuid.UUID,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
) -> Approval:
    return decide(db, tenant_id, approval_id, payload, "rejected")
