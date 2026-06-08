import uuid

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.gateway import ToolCallRequest
from app.services.gateway import GatewayService

router = APIRouter(prefix="/tenants/{tenant_id}/gateway", tags=["gateway"])
gateway_service = GatewayService()


@router.post("/tool-call")
def tool_call(
    tenant_id: uuid.UUID,
    payload: ToolCallRequest,
    db: Session = Depends(get_db),
) -> JSONResponse:
    result = gateway_service.execute(db, tenant_id, payload)
    # Security events must survive policy-denied and approval-required responses.
    db.commit()
    return JSONResponse(status_code=result.status_code, content=jsonable_encoder(result.body))

