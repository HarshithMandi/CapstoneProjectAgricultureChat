from app.api.routers.health import router as health_router
from app.api.routers.auth import router as auth_router
from app.api.routers.chat import router as chat_router
from app.api.routers.ingest import router as ingest_router
from app.api.routers.retrieval import router as retrieval_router

health = health_router
auth = auth_router
chat = chat_router
ingest = ingest_router
retrieval = retrieval_router
