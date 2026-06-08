import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Tenant, User
from app.db.session import get_db
from app.schemas.common import TenantOut, UserOut
from app.schemas.tenants import TenantCreate
from pydantic import BaseModel

router = APIRouter(prefix="/tenants", tags=["tenants"])


class UserCreate(BaseModel):
    email: str
    name: str
    role: str = "approver"


@router.post("", response_model=TenantOut, status_code=201)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)) -> Tenant:
    tenant = Tenant(name=payload.name)
    db.add(tenant)
    db.commit()
    return tenant


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: uuid.UUID, db: Session = Depends(get_db)) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(404, "Tenant not found")
    return tenant


@router.post("/{tenant_id}/users", response_model=UserOut, status_code=201)
def create_user(
    tenant_id: uuid.UUID, payload: UserCreate, db: Session = Depends(get_db)
) -> User:
    if db.get(Tenant, tenant_id) is None:
        raise HTTPException(404, "Tenant not found")
    user = User(tenant_id=tenant_id, **payload.model_dump())
    db.add(user)
    db.commit()
    return user

