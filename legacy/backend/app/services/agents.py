import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Agent


def get_active_agent(db: Session, tenant_id: uuid.UUID, agent_id: uuid.UUID) -> Agent | None:
    return db.scalar(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == tenant_id,
            Agent.status == "active",
        )
    )

