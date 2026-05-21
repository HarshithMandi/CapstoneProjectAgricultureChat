# Agri RAG Chatbot

AI-Powered Agriculture Domain Chatbot using RAG (Retrieval-Augmented Generation).

## Features

- Agriculture data collection from websites and documents
- Web scraping with content extraction and cleaning
- Text processing and chunking with LangChain
- Embedding generation using OpenRouter
- Vector storage with ChromaDB
- Conversational memory with MongoDB
- RAG-based question answering

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

3. Configure environment variables in `.env`

4. Run MongoDB (locally or via Docker)

5. Start the server:
```bash
uv run uvicorn app.main:app --reload
```

## API Endpoints

- `GET /health` - Health check
- `POST /ingest/url` - Ingest a single URL
- `POST /ingest/urls` - Ingest multiple URLs
- `POST /ingest/text` - Ingest raw text
- `POST /chat/sessions` - Create a new session
- `GET /chat/sessions/{session_id}` - Get session history
- `POST /chat/sessions/{session_id}/messages` - Send a message
- `POST /retrieval/search` - Semantic search
- `GET /retrieval/chunk/{chunk_id}` - Get a chunk

## Architecture

- **FastAPI** - Backend API
- **LangChain** - RAG pipeline
- **ChromaDB** - Vector database
- **MongoDB** - Session and message storage
- **OpenRouter** - LLM and embedding models