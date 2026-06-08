from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, approvals, checkpoints, events, gateway, health, policies, runs, tenants
from app.core.config import get_settings

app = FastAPI(
    title="OpenSteps API",
    version="0.1.0",
    description="Authorization gateway and tamper-evident ledger for AI-agent actions.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for api_router in (
    health.router,
    tenants.router,
    agents.router,
    runs.router,
    policies.router,
    gateway.router,
    approvals.router,
    events.router,
    checkpoints.router,
):
    app.include_router(api_router)

