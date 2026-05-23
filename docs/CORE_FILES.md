# Core Files Map

This document summarizes the primary files and their responsibilities in the Agri RAG Chatbot project.

- **app/main.py**: FastAPI application entry; registers routers, CORS middleware, and lifespan cleanup.

- **app/api/deps.py**: Dependency providers for FastAPI routes (service factories, auth, cleanup hooks).
- **app/api/routers/auth.py**: Authentication endpoints (register, login, admin seed, me).
- **app/api/routers/chat.py**: Chat and session endpoints, streaming SSE endpoint, and PDF upload endpoint.
- **app/api/routers/ingest.py**: Admin ingestion endpoints for text/URL/batch ingestion.
- **app/api/routers/retrieval.py**: Semantic search and chunk retrieval endpoints.
- **app/api/routers/health.py**: Simple health check endpoint.

- **app/services/chat_service.py**: Orchestrates chat flow: session management, retrieval, LLM calls, memory, and message persistence.
- **app/services/ingest_service.py**: Orchestrates scraping/processing/chunking/embedding and stores document records.
- **app/services/chunking_service.py**: Multi-granular text splitting (section/paragraph/semantic) and stable chunk id generation.
- **app/services/embedding_service.py**: Embedding orchestration and calls into the vectorstore adapter.
- **app/services/retrieval_service.py**: Thin wrapper that delegates to `langchain_components.retrievers`.
- **app/services/llm_service.py**: Wraps LLM API calls (synchronous + streaming) and context formatting.
- **app/services/memory_service.py**: Session-scoped conversational memory storage and retrieval.
- **app/services/scraping_service.py**: Web and PDF text extraction with fallbacks (trafilatura, readability, BeautifulSoup, pypdf).
- **app/services/processing_service.py**: Text normalization, metadata enrichment, and content post-processing.
- **app/services/embedding_service.py**: (If separate) handles batching and provider error handling for embeddings.

- **app/langchain_components/embeddings.py**: OpenRouter embedding adapter; sync/async clients and batching.
- **app/langchain_components/vectorstore.py**: Chroma adapter: add/search helper functions, id handling, and filter normalization.
- **app/langchain_components/retrievers.py**: Retriever wrapper that prefers semantic chunks and diversifies by source.
- **app/langchain_components/chains.py**: Prompt chaining and prompt templates used to format LLM inputs.
- **app/langchain_components/documents.py**: Helpers to create langchain `Document` objects with consistent metadata.
- **app/langchain_components/splitters.py**: Text splitter utilities for different chunk granularities.

- **app/db/chroma.py**: Chroma client and collection initialization (persistent directory handling).
- **app/db/mongo.py**: MongoDB client factory with in-memory fallback and graceful close.
- **app/db/repositories/document.py**: Document repository for storing document records and chunk references.
- **app/db/repositories/session.py**: Session repository for chat sessions.
- **app/db/repositories/message.py**: Message repository for chat messages.
- **app/db/repositories/user.py**: User repository for auth and admin management.

- **app/core/config.py**: Application configuration (pydantic settings) and environment variable defaults.
- **app/core/exceptions.py**: Custom application exceptions (IngestionError, RetrievalError, LLMError, etc.).
- **app/core/logging.py**: Logging setup and format configuration.

- **app/utils/text.py**: Text cleaning, agriculture keyword detection, guardrail logic, and id helpers.
- **app/utils/ids.py**: Stable id generation helpers (doc_id, chunk_id).
- **app/utils/metadata.py**: Metadata helpers used when creating documents/chunks.

- **app/schemas/**: Pydantic request/response models:
  - `chat.py`: Chat request/response and session models.
  - `ingest.py`: Ingest endpoints payload schemas.
  - `retrieval.py`: Search and retrieval schemas.

- **frontend/src/main.jsx**: Single-page React UI, chat components, file upload/dropzone, and SSE streaming client.
- **frontend/src/styles.css**: UI styles and dropzone/composer styling.

- **scripts/build_rag_db.py**: End-to-end crawler + scrape + process + ingest pipeline to build the RAG DB.
- **scripts/ingest_offline_corpus.py**: Utility to ingest a local corpus of .txt/.md/.pdf files.
- **scripts/reindex.py**: Reindex or rebuild vectorstore utility.
- **scripts/run_api.py**: Helper that starts the API using the repo venv (works when `uvicorn` isn't in PATH).

- **requirements.txt / pyproject.toml**: Dependency lists used to install runtime/test deps.
- **tests/test_api.py**: Basic integration tests for health, auth, and retriever logic.
- **README.md**: Setup and developer documentation (startup, API surface, architecture overview).

If you'd like, I can:
- add links to each file in this doc (file-path links),
- expand any section into per-function descriptions, or
- generate a CSV/JSON mapping for programmatic use.
