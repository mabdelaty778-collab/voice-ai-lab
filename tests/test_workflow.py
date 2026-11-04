from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient

from voice_ai_lab.api import create_app
from voice_ai_lab.config import Settings
from voice_ai_lab.models import LeadInput
from voice_ai_lab.store import Store


def sample(**changes):
    return {
        "name": "Demo Learner",
        "email": "learner@example.com",
        "course_id": "voice-agents",
        "consent": True,
        "request_id": str(uuid4()),
        **changes,
    }


def test_full_workflow_and_durable_restart(client, headers, settings):
    question = client.post("/api/v1/questions", headers=headers, json={"text": "voice agents"})
    assert question.status_code == 200
    assert "voice-agents" in question.json()["data"]["sources"]
    assert question.json()["data"]["mode"] == "simulation"
    created = client.post("/api/v1/leads", headers=headers, json=sample())
    assert created.status_code == 201
    assert created.json()["persisted"] is True
    # An independent app/store instance can read the committed row after restart.
    with TestClient(create_app(settings)) as restarted:
        listing = restarted.get("/api/v1/leads", headers=headers).json()
        assert listing["meta"]["total"] == 1
        assert listing["data"][0]["id"] == created.json()["data"]["id"]


def test_retries_are_idempotent(client, headers):
    data = sample()
    first = client.post("/api/v1/leads", headers=headers, json=data)
    again = client.post("/api/v1/leads", headers=headers, json=data)
    assert first.status_code == 201
    assert again.status_code == 200
    assert again.json()["replayed"] is True
    assert first.json()["data"]["id"] == again.json()["data"]["id"]
    assert (
        client.get("/api/v1/metrics", headers=headers).json()["data"]["persisted_test_leads"] == 1
    )


def test_reusing_request_id_with_different_payload_returns_conflict(client, headers):
    data = sample()
    client.post("/api/v1/leads", headers=headers, json=data)
    response = client.post("/api/v1/leads", headers=headers, json={**data, "name": "Other Learner"})
    assert response.status_code == 409
    assert "Other Learner" not in response.text


def test_concurrent_retries_create_one_row(settings):
    store = Store(settings.db_path)
    store.initialize()
    lead = LeadInput(**sample())
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: store.capture(lead), range(12)))
    assert sum(created for _, created in results) == 1
    assert store.leads(100, 0)[1] == 1


def test_simulated_failure_never_confirms_success(settings, headers):
    failed = Settings(api_key=settings.api_key, db_path=settings.db_path, fail_writes=True)
    data = sample()
    with TestClient(create_app(failed)) as client:
        response = client.post("/api/v1/leads", headers=headers, json=data)
        assert response.status_code == 503
        assert "persisted" not in response.json()
        assert client.get("/api/v1/leads", headers=headers).json()["meta"]["total"] == 0
    # Recover the DB, replay the original request and commit once.
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/v1/leads", headers=headers, json=data).status_code == 201
        assert client.post("/api/v1/leads", headers=headers, json=data).status_code == 200


def test_real_sql_failure_is_not_acknowledged(client, settings, headers):
    with client.app.state.store._connect() as db:
        db.execute("DROP TABLE leads")
    response = client.post("/api/v1/leads", headers=headers, json=sample())
    assert response.status_code == 503
    assert "saved" in response.json()["error"]["message"]
    assert "sqlite" not in response.text.lower()


def test_transaction_rolls_back_if_event_write_fails(client, headers):
    with client.app.state.store._connect() as db:
        db.execute("DROP TABLE events")
    response = client.post("/api/v1/leads", headers=headers, json=sample())
    assert response.status_code == 503
    assert client.get("/api/v1/leads", headers=headers).json()["meta"]["total"] == 0


def test_sql_content_is_stored_as_data(client, headers):
    name = "Demo'); DROP TABLE leads;--"
    response = client.post("/api/v1/leads", headers=headers, json=sample(name=name))
    assert response.status_code == 201
    rows = client.get("/api/v1/leads", headers=headers).json()["data"]
    assert rows[0]["name"] == name
