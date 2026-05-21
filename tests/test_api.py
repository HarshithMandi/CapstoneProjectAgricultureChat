import pytest
from app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_session():
    response = client.post("/chat/sessions", json={})
    assert response.status_code == 200
    assert "id" in response.json()


def test_ingest_text():
    response = client.post("/ingest/text", json={
        "text": "Rice leaf blight is a common disease. Symptoms include yellowing leaves.",
        "title": "Rice Disease Guide",
        "source": "test",
        "topic": "crop-diseases"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"