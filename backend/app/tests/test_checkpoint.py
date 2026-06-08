from fastapi.testclient import TestClient

from app.core.canonical_json import canonical_json
from app.core.crypto import verify_signature
from app.services.checkpoints import service_public_key
from app.tests.helpers import setup_demo


def test_checkpoint_creation_signs_merkle_root(client: TestClient) -> None:
    setup = setup_demo(client)
    response = client.post(f"/tenants/{setup['tenant_id']}/checkpoints", json={})
    assert response.status_code == 201, response.text
    checkpoint = response.json()
    payload = {
        "id": checkpoint["id"],
        "tenant_id": setup["tenant_id"],
        "from_event_id": checkpoint["from_event_id"],
        "to_event_id": checkpoint["to_event_id"],
        "merkle_root": checkpoint["merkle_root"],
        "event_count": checkpoint["event_count"],
    }
    assert verify_signature(
        service_public_key(), canonical_json(payload), checkpoint["signature"]
    )
    verification = client.post(
        f"/tenants/{setup['tenant_id']}/ledger/verify", json={}
    )
    assert verification.json()["verified"] is True

