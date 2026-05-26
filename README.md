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

3. Configure environment variables in `.env` (see `.env.example` for required variables)

4. Start the backend server:
```bash
uv run uvicorn app.main:app --reload
```

Alternative methods:
```bash
# Direct Python execution
python3 scripts/run_api.py

# Using uvicorn directly (if installed)
uvicorn app.main:app --reload
```

5. Start the React frontend:
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

- **FastAPI** - Backend API framework providing REST endpoints
- **LangChain** - RAG pipeline orchestration, document processing, and chain management
- **ChromaDB** - Vector database for storing and retrieving document embeddings
- **MongoDB** - Primary database for user accounts, chat sessions, and message history
- **OpenRouter** - Unified API for accessing various LLM and embedding models
- **React + Vite** - Role-aware frontend dashboard with real-time chat capabilities

### Data Flow
1. **Knowledge Ingestion**: Administrators ingest content via URLs or raw text → Content is scraped/processed → Text is chunked → Embeddings generated → Stored in ChromaDB
2. **Chat Processing**: Users send messages → Session retrieved from MongoDB → Relevant context retrieved from ChromaDB → LLM generates response using RAG → Response stored in MongoDB

### Security
- JWT-based authentication for API endpoints
- Role-based access control (admin/user)
- Environment variable configuration for sensitive data
- CORS middleware for frontend-backend communication

## Directory Structure

```
app/
├── api/
│   ├── deps.py          # Dependency injection (database connections)
│   └── routers/         # FastAPI route handlers
│       ├── auth.py      # Authentication endpoints
│       ├── chat.py      # Chat session and message endpoints
│       ├── health.py    # Health check endpoints
│       ├── ingest.py    # Knowledge ingestion endpoints
│       └── retrieval.py # Document retrieval endpoints
├── core/                # Application configuration and utilities
│   ├── config.py        # Environment variable management
│   ├── exceptions.py    # Custom exception classes
│   └── logging.py       # Logging configuration
├── db/                  # Database connections and repositories
│   ├── chroma.py        # ChromaDB client wrapper
│   ├── mongo.py         # MongoDB client wrapper
│   └── repositories/    # Data access layer
│       ├── chat.py      # Chat session operations
│       ├── message.py   # Message operations
│       └── document.py  # Document/chunk operations
├── langchain_components/# LangChain integrations
│   ├── embeddings.py    # OpenRouter embedding models
│   ├── retriever.py     # ChromaDB retriever wrapper
│   └── chains.py        # RAG chain configurations
├── prompts/             # LLM prompt templates
├── schemas/             # Pydantic models for request/response validation
├── services/            # Business logic implementations
│   ├── chat_service.py      # Chat session management
│   ├── chunking_service.py  # Text chunking strategies
│   ├── embedding_service.py # Embedding generation
│   ├── ingest_service.py    # Knowledge ingestion pipeline
│   ├── llm_service.py       # LLM interaction wrapper
│   ├── memory_service.py    # Chat history management
│   ├── processing_service.py# Document processing utilities
│   ├── retrieval_service.py # Semantic search operations
│   └── scraping_service.py  # Web content extraction
├── main.py              # FastAPI application entry point
└── utils/               # Cross-cutting utility functions

scripts/                 # Utility and maintenance scripts
├── build_rag_db.py      # Build knowledge base from seed data
├─ ingest_offline_corpus.py # Ingest documents from local files
├─ ingest_seed_data.py   # Initial knowledge base population
├─ reindex.py            # Rebuild vector indexes
├─ run_api.py            # Alternative backend startup script
├─ snapshot_rag_db.py    # Backup knowledge base
└─ sources.json          # Default ingestion sources

data/                    # Data storage directories
├── raw/                 # Unprocessed source documents
└── processed/           # Processed documents and chunks

frontend/                # React + Vite frontend application
├── src/
│   ├── components/      # Reusable UI components
│   ├── pages/           # Application pages
│   ├── hooks/           # Custom React hooks
│   ├── contexts/        # React context providers
│   ├── services/        # API service wrappers
│   ├── utils/           # Frontend utilities
│   └── App.jsx          # Main application component
├── public/              # Static assets
├── index.html           # HTML entry point
├── vite.config.js       # Vite configuration
├── package.json         # Dependencies and scripts
└── .env.example         # Frontend environment variables
```
