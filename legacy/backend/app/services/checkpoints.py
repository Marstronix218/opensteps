import uuid
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.canonical_json import canonical_json
from app.core.config import get_settings
from app.core.crypto import generate_keypair, public_key_from_private, sign_payload
from app.core.merkle import compute_merkle_root
from app.db.models import Checkpoint, Event
from app.services.ledger import EventData, ledger_service


@lru_cache
def service_private_key() -> str:
    configured = get_settings().service_private_key
    return configured if configured else generate_keypair()[0]


def service_public_key() -> str:
    return public_key_from_private(service_private_key())


class CheckpointService:
    def create(self, db: Session, tenant_id: uuid.UUID) -> Checkpoint:
        events = list(
            db.scalars(
                select(Event)
                .where(Event.tenant_id == tenant_id)
                .order_by(Event.timestamp.asc(), Event.id.asc())
            )
        )
        previous = db.scalar(
            select(Checkpoint)
            .where(Checkpoint.tenant_id == tenant_id)
            .order_by(Checkpoint.created_at.desc())
            .limit(1)
        )
        if previous:
            indexes = [index for index, item in enumerate(events) if item.id == previous.to_event_id]
            if not indexes:
                raise ValueError("Previous checkpoint boundary event is missing")
            events = events[indexes[0] + 1 :]
        if not events:
            raise ValueError("No new events are available for checkpointing")

        merkle_root = compute_merkle_root([item.event_hash for item in events])
        checkpoint_id = uuid.uuid4()
        payload = {
            "id": str(checkpoint_id),
            "tenant_id": str(tenant_id),
            "from_event_id": str(events[0].id),
            "to_event_id": str(events[-1].id),
            "merkle_root": merkle_root,
            "event_count": len(events),
        }
        checkpoint = Checkpoint(
            id=checkpoint_id,
            tenant_id=tenant_id,
            from_event_id=events[0].id,
            to_event_id=events[-1].id,
            merkle_root=merkle_root,
            event_count=len(events),
            signature=sign_payload(service_private_key(), canonical_json(payload)),
        )
        db.add(checkpoint)
        db.flush()
        ledger_service.append(
            db,
            EventData(
                tenant_id=tenant_id,
                run_id=events[-1].run_id,
                event_type="checkpoint.created",
                parent_event_id=events[-1].id,
                output_hash=merkle_root,
            ),
        )
        return checkpoint


checkpoint_service = CheckpointService()

