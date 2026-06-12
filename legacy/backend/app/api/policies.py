import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Agent, Policy, Tenant
from app.db.session import get_db
from app.schemas.common import PolicyOut
from app.schemas.policies import PolicyCreate, PolicyDecisionOut, PolicyEvaluate
from app.services.policies import policy_engine

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["policies"])


@router.post("/policies", response_model=PolicyOut, status_code=201)
def create_policy(
    tenant_id: uuid.UUID, payload: PolicyCreate, db: Session = Depends(get_db)
) -> Policy:
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(404, "Tenant not found")
    try:
        policy_engine.evaluate_document(
            payload.policy_yaml, agent="validation", tool="validation", action="validation", resource="validation"
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    policy = Policy(tenant_id=tenant_id, **payload.model_dump())
    db.add(policy)
    db.commit()
    return policy


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Policy]:
    return list(
        db.scalars(
            select(Policy)
            .where(Policy.tenant_id == tenant_id)
            .order_by(Policy.created_at.desc())
        )
    )


@router.put("/policies/{policy_id}", response_model=PolicyOut)
def update_policy(
    tenant_id: uuid.UUID,
    policy_id: uuid.UUID,
    payload: PolicyCreate,
    db: Session = Depends(get_db),
) -> Policy:
    policy = db.get(Policy, policy_id)
    if policy is None or policy.tenant_id != tenant_id:
        raise HTTPException(404, "Policy not found")
    try:
        policy_engine.evaluate_document(
            payload.policy_yaml,
            agent="validation",
            tool="validation",
            action="validation",
            resource="validation",
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    policy.name = payload.name
    policy.policy_yaml = payload.policy_yaml
    db.commit()
    return policy


@router.post("/policy/evaluate", response_model=PolicyDecisionOut)
def evaluate_policy(
    tenant_id: uuid.UUID, payload: PolicyEvaluate, db: Session = Depends(get_db)
) -> PolicyDecisionOut:
    agent = db.get(Agent, payload.agent_id)
    if agent is None or agent.tenant_id != tenant_id:
        raise HTTPException(404, "Agent not found")
    result = policy_engine.evaluate(
        db, tenant_id=tenant_id, agent=agent, tool=payload.tool, action=payload.action, resource=payload.resource
    )
    return PolicyDecisionOut(decision=result.decision, matched_rule=result.matched_rule)
