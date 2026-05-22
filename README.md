# Agri RAG Chatbot

AI-Powered Agriculture Domain Chatbot using RAG (Retrieval-Augmented Generation). This application provides intelligent assistance to farmers and agricultural professionals by retrieving and generating accurate answers from a knowledge base of agricultural content.

## Overview

The Agri RAG Chatbot is designed to answer questions related to agriculture, farming practices, crop management, soil health, pest control, and more. It uses a Retrieval-Augmented Generation architecture to provide contextually relevant responses backed by source documentation.

## Features

- **Agriculture-focused conversations** - Automatically detects and responds only to farming-related queries
- **Knowledge ingestion** - Web scraping and document processing for building the knowledge base
- **Text processing and chunking** - Multi-granular text splitting with LangChain
- **Embedding generation** - Using OpenRouter models for vector representations
- **Vector storage** - ChromaDB for efficient similarity search
- **Conversational memory** - MongoDB-backed session and message storage
- **RAG-based question answering** - Context-aware responses with source citations

## Setup

1. Install dependencies:
```bash
uv sync
```

If you're not using `uv`, you can also use the included virtual environment:
```bash
cd agri-rag-chatbot
source .venv/bin/activate
pip install -r requirements.txt
```

Note: This repo also includes a `venv` symlink to `.venv`, so `source venv/bin/activate` works too.

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

Alternative (works even when `uvicorn` isn't on your PATH):
```bash
python3 scripts/run_api.py
```

6. Start the React frontend:
```bash
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:5173` and calls the backend at `http://localhost:8000`. Set `VITE_API_URL` in `frontend/.env` if your backend runs elsewhere.

## API Endpoints

### Auth & Admin
- `POST /auth/register` - Create a standard user account
- `GET /auth/admin-setup/status` - Check whether an admin account exists
- `POST /auth/admin-setup` - Create the initial admin account when no admin exists
- `POST /auth/login` - Login and receive a JWT bearer token
- `GET /auth/me` - Get the authenticated user
- `GET /admin/users` - Admin-only user listing
- `PATCH /admin/users/{user_id}` - Admin-only role/status update

### Health
- `GET /health` - Health check

### Knowledge Ingestion
- `POST /ingest/url` - Admin-only ingestion of a single URL into the knowledge base
- `POST /ingest/urls` - Admin-only ingestion of multiple URLs into the knowledge base
- `POST /ingest/text` - Admin-only ingestion of raw text content into the knowledge base

### Chat & Sessions
- `POST /chat/sessions` - Authenticated users create a new chat session
- `GET /chat/sessions/{session_id}` - Get session history
- `POST /chat/sessions/{session_id}/messages` - Send a message to a session (non-streaming)
- `POST /chat/sessions/{session_id}/messages/stream` - Send a message with streaming response

### Retrieval
- `POST /retrieval/search` - Admin-only semantic search across ingested documents
- `GET /retrieval/chunk/{chunk_id}` - Admin-only retrieval of a specific chunk by ID

## Core Functions

### ChatService
- `create_session(title)` - Create a new chat session with optional title
- `get_session(session_id)` - Retrieve a session by ID with message history
- `send_message(session_id, message)` - Send a message and receive a complete response
- `stream_message(session_id, message)` - Stream response tokens as they're generated

### IngestService
- `ingest_url(url, title, topic)` - Scrape, process, and store content from a URL
- `ingest_urls(urls, topic)` - Batch ingest multiple URLs
- `ingest_text(text, title, source, topic, document_type)` - Ingest raw text content
- `close()` - Cleanup resources

### RetrievalService
- `search(query, top_k)` - Perform semantic search returning relevant chunks
- `get_chunk_by_id(chunk_id)` - Retrieve a specific chunk by its ID

## Architecture

- **FastAPI** - Backend API framework
- **LangChain** - RAG pipeline and document processing
- **ChromaDB** - Vector database for embeddings
- **MongoDB** - User, session, and message storage
- **OpenRouter** - LLM and embedding models
- **React + Vite** - Role-aware frontend dashboard

## Directory Structure

```
app/
├── api/
│   └── routers/       # FastAPI route handlers (auth, chat, ingest, retrieval, health)
├── services/          # Business logic services (chat, ingest, retrieval, etc.)
├── langchain_components/  # LangChain utilities (embeddings, retrievers, chains)
├── db/
│   ├── chroma.py      # ChromaDB client
│   ├── mongo.py       # MongoDB client
│   └── repositories/  # Data access layer (session, message, document)
├── core/              # Configuration, logging, exceptions
├── utils/             # Utility functions
├── schemas/           # Pydantic models for API
└── prompts/           # LLM prompt templates
scripts/              # Utility scripts for data ingestion
data/                 # Raw and processed data storage
frontend/             # React + Vite frontend application
```
