from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_session_requires_auth():
    response = client.post("/chat/sessions", json={})
    assert response.status_code == 401


def test_ingest_text_requires_auth():
    response = client.post("/ingest/text", json={
        "text": "Rice leaf blight is a common disease. Symptoms include yellowing leaves.",
        "title": "Rice Disease Guide",
        "source": "test",
        "topic": "crop-diseases"
    })
    assert response.status_code == 401
