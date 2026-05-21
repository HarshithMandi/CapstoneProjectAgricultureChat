from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import auth_router, health_router, chat_router, ingest_router, retrieval_router
from app.api.deps import close_chat_service
from app.db.mongo import close_mongo_client
from app.core.config import settings
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(ingest_router)
app.include_router(retrieval_router)
