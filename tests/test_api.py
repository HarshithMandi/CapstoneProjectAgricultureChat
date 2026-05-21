import importlib

from app.langchain_components.retrievers import RetrieverService
from app.main import app
from fastapi.testclient import TestClient


auth_module = importlib.import_module("app.api.routers.auth")
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


def test_admin_setup_status_when_no_admin(monkeypatch):
    class FakeUserRepository:
        async def count_by_role(self, role):
            assert role == "admin"
            return 0

    monkeypatch.setattr(auth_module, "UserRepository", FakeUserRepository)

    response = client.get("/auth/admin-setup/status")

    assert response.status_code == 200
    assert response.json() == {"has_admin": False}


def test_admin_setup_creates_admin_when_missing(monkeypatch):
    class FakeUserRepository:
        async def count_by_role(self, role):
            assert role == "admin"
            return 0

        async def get_by_email(self, email):
            return None

        async def create(self, email, password_hash, role="user", full_name=None):
            return {
                "_id": "507f1f77bcf86cd799439011",
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "role": role,
                "is_active": True,
                "created_at": "2026-05-22T00:00:00",
            }

    monkeypatch.setattr(auth_module, "UserRepository", FakeUserRepository)

    response = client.post(
        "/auth/admin-setup",
        json={"email": "Admin@Example.com", "password": "password123", "full_name": "Admin User"},
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "admin@example.com"
    assert response.json()["user"]["role"] == "admin"


def test_admin_setup_rejects_when_admin_exists(monkeypatch):
    class FakeUserRepository:
        async def count_by_role(self, role):
            assert role == "admin"
            return 1

    monkeypatch.setattr(auth_module, "UserRepository", FakeUserRepository)

    response = client.post(
        "/auth/admin-setup",
        json={"email": "admin@example.com", "password": "password123"},
    )

    assert response.status_code == 409


def test_retriever_diversifies_sources():
    class FakeDoc:
        def __init__(self, chunk_id, source):
            self.metadata = {"chunk_id": chunk_id, "source": source}

    service = RetrieverService(embeddings=object())
    docs = [
        (FakeDoc("wiki-1", "https://en.wikipedia.org/wiki/Agriculture"), 0.1),
        (FakeDoc("wiki-2", "https://en.wikipedia.org/wiki/Agriculture"), 0.2),
        (FakeDoc("wiki-3", "https://en.wikipedia.org/wiki/Agriculture"), 0.3),
        (FakeDoc("fao-1", "https://www.fao.org/3/y3557e/y3557e00.htm"), 0.4),
        (FakeDoc("wa-1", "https://www.agric.wa.gov.au/"), 0.5),
    ]

    selected = service._diversify_by_source(docs, top_k=3)

    assert [doc.metadata["chunk_id"] for doc, _score in selected] == ["wiki-1", "fao-1", "wa-1"]
