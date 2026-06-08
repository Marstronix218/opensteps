import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.hashing import compute_event_hash
from app.db.models import Event, Tenant


@dataclass
class EventData:
    tenant_id: uuid.UUID
    run_id: uuid.UUID
    event_type: str
    parent_event_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    tool: str | None = None
    action: str | None = None
    resource: str | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    policy_decision: str | None = None
    approval_id: uuid.UUID | None = None
    signature: str | None = None
    raw_payload_encrypted: str | None = None


class LedgerService:
    def append(self, db: Session, data: EventData) -> Event:
        # PostgreSQL row locking serializes each tenant's hash chain.
        db.execute(select(Tenant.id).where(Tenant.id == data.tenant_id).with_for_update())
        previous = db.scalar(
            select(Event)
            .where(Event.tenant_id == data.tenant_id)
            .order_by(Event.timestamp.desc(), Event.id.desc())
            .limit(1)
        )
        event = Event(
            id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            previous_hash=previous.event_hash if previous else None,
            event_hash="pending",
            **data.__dict__,
        )
        event.event_hash = compute_event_hash(event.hash_body(), event.previous_hash)
        db.add(event)
        db.flush()
        return event

    def verify(
        self, db: Session, tenant_id: uuid.UUID, run_id: uuid.UUID | None = None
    ) -> dict[str, Any]:
        # Verify the complete tenant chain even when returning the subset for a run.
        events = list(
            db.scalars(
                select(Event)
                .where(Event.tenant_id == tenant_id)
                .order_by(Event.timestamp.asc(), Event.id.asc())
            )
        )
        expected_previous: str | None = None
        errors: list[str] = []
        checked = 0
        selected_ids: list[uuid.UUID] = []
        for item in events:
            belongs = run_id is None or item.run_id == run_id
            calculated = compute_event_hash(item.hash_body(), item.previous_hash)
            if item.previous_hash != expected_previous:
                errors.append(
                    f"event {item.id}: previous_hash mismatch "
                    f"(expected {expected_previous}, got {item.previous_hash})"
                )
            if item.event_hash != calculated:
                errors.append(
                    f"event {item.id}: event_hash mismatch "
                    f"(expected {calculated}, got {item.event_hash})"
                )
            expected_previous = item.event_hash
            if belongs:
                checked += 1
                selected_ids.append(item.id)
        return {
            "verified": not errors,
            "checked_events": checked,
            "first_event_id": selected_ids[0] if selected_ids else None,
            "last_event_id": selected_ids[-1] if selected_ids else None,
            "errors": errors,
        }


ledger_service = LedgerService()

