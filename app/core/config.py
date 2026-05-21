from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    OPENROUTER_API_KEY: str = Field(..., description="OpenRouter API key")
    MONGODB_URI: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URI")
    MONGODB_DB: str = Field(default="agri_rag_chatbot", description="MongoDB database name")
    CHROMA_PERSIST_DIR: str = Field(default="./chroma_db", description="ChromaDB persistence directory")
    CHROMA_COLLECTION_NAME: str = Field(default="agri_documents", description="ChromaDB collection name")

    JWT_SECRET_KEY: str = Field(default="change-me-in-production", description="Secret key used to sign JWTs")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=1440, description="Access token lifetime in minutes")
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated frontend origins allowed to call the API",
    )

    LLM_MODEL: str = Field(default="openai/gpt-oss-120b:free", description="LLM model identifier")
    EMBEDDING_MODEL: str = Field(default="nvidia/llama-nemotron-embed-vl-1b-v2:free", description="Embedding model identifier")

    EMBEDDINGS_BATCH_SIZE: int = Field(default=64, description="Max texts per embeddings API call")

    LOG_LEVEL: str = Field(default="INFO", description="Logging level")


settings = Settings()
