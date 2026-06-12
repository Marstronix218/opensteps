import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Approval


def utc_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def validate_approval(
    db: Session,
    *,
    approval_id: uuid.UUID,
    tenant_id: uuid.UUID,
    run_id: uuid.UUID,
    scope: dict[str, Any],
) -> tuple[Approval | None, str | None]:
    approval = db.get(Approval, approval_id)
    if approval is None or approval.tenant_id != tenant_id or approval.run_id != run_id:
        return None, "Approval does not exist for this tenant and run"
    if approval.status != "approved":
        return None, f"Approval is {approval.status}, not approved"
    if utc_aware(approval.expires_at) <= datetime.now(timezone.utc):
        return None, "Approval has expired"
    if approval.scope_json != scope:
        return None, "Approval scope does not match this request"
    return approval, None

