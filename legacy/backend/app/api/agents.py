import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Agent, Tenant
from app.db.session import get_db
from app.schemas.agents import AgentCreate
from app.schemas.common import AgentOut

router = APIRouter(prefix="/tenants/{tenant_id}/agents", tags=["agents"])


@router.post("", response_model=AgentOut, status_code=201)
def create_agent(
    tenant_id: uuid.UUID, payload: AgentCreate, db: Session = Depends(get_db)
) -> Agent:
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(404, "Tenant not found")
    agent = Agent(tenant_id=tenant_id, **payload.model_dump())
    db.add(agent)
    db.commit()
    return agent


@router.get("", response_model=list[AgentOut])
def list_agents(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Agent]:
    return list(db.scalars(select(Agent).where(Agent.tenant_id == tenant_id)))


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(
    tenant_id: uuid.UUID, agent_id: uuid.UUID, db: Session = Depends(get_db)
) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.tenant_id != tenant_id:
        raise HTTPException(404, "Agent not found")
    return agent

