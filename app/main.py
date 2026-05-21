from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routers import auth_router, health_router, chat_router, ingest_router, retrieval_router
from app.api.deps import close_chat_service
from app.db.mongo import close_mongo_client
from app.core.logging import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_chat_service()
    await close_mongo_client()


app = FastAPI(
    title="Agri RAG Chatbot",
    description="AI-Powered Agriculture Domain Chatbot using RAG",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(ingest_router)
app.include_router(retrieval_router)
