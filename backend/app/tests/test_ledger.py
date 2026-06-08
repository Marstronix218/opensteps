from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Event, Run, Tenant
from app.services.ledger import EventData, ledger_service


def test_hash_chain_verifies_and_detects_tampering(
    db_factory: sessionmaker[Session],
) -> None:
    with db_factory() as db:
        tenant = Tenant(name="Ledger tenant")
        db.add(tenant)
        db.flush()
        run = Run(tenant_id=tenant.id)
        db.add(run)
        db.flush()
        first = ledger_service.append(
            db, EventData(tenant_id=tenant.id, run_id=run.id, event_type="run.started")
        )
        second = ledger_service.append(
            db,
            EventData(
                tenant_id=tenant.id,
                run_id=run.id,
                event_type="policy.evaluated",
                parent_event_id=first.id,
                policy_decision="allowed",
            ),
        )
        db.commit()

        verified = ledger_service.verify(db, tenant.id)
        assert verified["verified"] is True
        assert verified["checked_events"] == 2
        assert second.previous_hash == first.event_hash

        db.execute(
            update(Event).where(Event.id == first.id).values(policy_decision="tampered")
        )
        db.commit()
        db.expire_all()
        failed = ledger_service.verify(db, tenant.id)
        assert failed["verified"] is False
        assert str(first.id) in failed["errors"][0]

