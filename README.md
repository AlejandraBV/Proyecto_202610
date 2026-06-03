# Academic Content Generator

An AI-powered platform for university teachers to generate, review, and manage academic content. Built with FastAPI, Next.js, LangGraph, and Google Gemini via Vertex AI.

---

## Table of Contents

1. [Features](#features)
2. [Architecture Overview](#architecture-overview)
3. [Project Structure](#project-structure)
4. [Technology Stack](#technology-stack)
5. [How Everything Works](#how-everything-works)
   - [Content Generation Pipeline (LangGraph)](#content-generation-pipeline-langgraph)
   - [RAG Pipeline](#rag-pipeline)
   - [Conversation Routing](#conversation-routing)
   - [Human-in-the-Loop (HITL)](#human-in-the-loop-hitl)
   - [SSE Streaming](#sse-streaming)
   - [RAGAS Evaluation](#ragas-evaluation)
6. [API Endpoints](#api-endpoints)
7. [Database Schema](#database-schema)
8. [Configuration](#configuration)
9. [Setup & Running](#setup--running)
10. [Google Cloud / Vertex AI Connection](#google-cloud--vertex-ai-connection)

---

## Features

- **AI Content Generation** — exams, study guides, slideshows, question banks, and free-form text via Gemini 2.5 Flash
- **LangGraph Pipeline** — deterministic multi-agent workflow: fetch context → analyze → generate → review → (loop or finish)
- **RAG (Retrieval-Augmented Generation)** — upload PDF, DOCX, or TXT files; content is chunked, embedded, and stored in ChromaDB for context-aware generation
- **Intelligent Conversation Routing** — messages are classified by subject/topic; a new conversation is auto-created only when the topic genuinely changes
- **Human-in-the-Loop (HITL)** — teachers can approve, correct, or reject generated content; the system learns from corrections via few-shot injection
- **SSE Streaming** — generated text streams to the UI in real time using Server-Sent Events
- **RAGAS Evaluation** — per-message quality metrics: faithfulness, answer relevance, context precision
- **Bloom's Taxonomy Tagging** — every assistant response is automatically tagged with Bloom levels (Remember → Create)
- **Folder Organisation** — conversations are automatically grouped into subject folders; teachers can rename, recolour, or move them
- **Question Bank** — individual questions can be saved from generated exams and reused across sessions
- **Audit Trail** — full log of every content generation decision, agent action, and classification correction
- **Export** — generated content can be exported as PDF or DOCX
- **Multilingual UI** — English / Spanish toggle

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                          │
│   Pages: dashboard, documents, evaluation, history, question-   │
│   bank, settings, login, register                                │
│   State: Zustand (appStore)    UI: Tailwind CSS                  │
└────────────────────────┬────────────────────────────────────────┘
                         │  HTTP / SSE  (localhost:3000 → :8000)
┌────────────────────────▼────────────────────────────────────────┐
│                        FastAPI Backend                           │
│                                                                  │
│  Routers: auth · conversations · documents · folders ·          │
│           feedback · export · evaluation · audit · question_bank │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              LangGraph Orchestrator                      │    │
│  │  fetch_context → analyze → generate → review → result   │    │
│  │       (AnalyzerAgent) (GeneratorAgent) (ReviewerAgent)   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Services: ConversationService · DocumentIngestionService ·     │
│            EvaluationService · VectorService · LLMService       │
└──────────┬─────────────────────────────┬────────────────────────┘
           │                             │
┌──────────▼──────────┐   ┌─────────────▼──────────────────────┐
│   PostgreSQL 16      │   │  ChromaDB (vector store)           │
│   (primary store)    │   │  Document chunks + embeddings      │
│   Tables: users,     │   │  Persisted at /app/chromadb_data   │
│   conversations,     │   └────────────────────────────────────┘
│   messages, docs,    │
│   generated_contents,│   ┌────────────────────────────────────┐
│   folders, questions,│   │  Google Vertex AI                  │
│   feedback_records,  │   │  Model: gemini-2.5-flash           │
│   agent_decisions,   │   │  Auth: service account credentials │
│   message_ratings,   │   │  SDK: google-genai                 │
│   classification_    │   └────────────────────────────────────┘
│   corrections, ...   │
└──────────────────────┘
```

---

## Project Structure

```
Proyecto_202610/
├── docker-compose.yml          # Orchestrates postgres + backend + frontend
├── .env.example                # Environment variable template
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # FastAPI app entry point; registers all routers
│   └── app/
│       ├── api/                # HTTP route handlers
│       │   ├── __init__.py     # Exports all routers
│       │   ├── auth.py         # POST /auth/register, /auth/login, GET /auth/me
│       │   ├── conversations.py# CRUD + message routing + SSE stream endpoint
│       │   ├── documents.py    # Upload, list, delete documents
│       │   ├── folders.py      # CRUD for subject folders
│       │   ├── feedback.py     # Thumbs-up/down on messages
│       │   ├── export.py       # Export content as PDF or DOCX
│       │   ├── evaluation.py   # RAGAS metrics per conversation
│       │   ├── audit.py        # Agent decision & classification audit log
│       │   ├── question_bank.py# Save, list, search individual questions
│       │   └── health.py       # GET /health
│       │
│       ├── agents/             # Individual AI agents
│       │   ├── analyzer_agent.py   # Interprets user prompt + retrieves RAG context
│       │   ├── generator_agent.py  # Calls LLM to produce content
│       │   ├── reviewer_agent.py   # Scores content; decides approve/regenerate
│       │   ├── metadata_analyzer.py# Hybrid keyword+LLM topic & subject detection
│       │   └── feedback_agent.py   # Processes teacher corrections
│       │
│       ├── orchestration/
│       │   ├── langgraph_orchestrator.py  # LangGraph StateGraph definition
│       │   └── content_orchestrator.py    # Entry point; invokes LangGraph graph
│       │
│       ├── services/
│       │   ├── llm_service.py              # Vertex AI Gemini wrapper (async + simulated stream)
│       │   ├── vector_service.py           # ChromaDB read/write helpers
│       │   ├── document_ingestion_service.py # PDF/DOCX/TXT parsing + chunking
│       │   ├── conversation_service.py     # Conversation CRUD + topic routing logic
│       │   ├── evaluation_service.py       # RAGAS-style metric computation
│       │   ├── user_service.py             # User CRUD helpers
│       │   └── feedback_learning_service.py# Stores & applies HITL corrections
│       │
│       ├── models/
│       │   └── models.py       # All SQLAlchemy ORM models
│       ├── schemas/
│       │   ├── schemas.py      # All Pydantic request/response schemas
│       │   └── __init__.py     # Re-exports all schemas
│       ├── core/
│       │   ├── config.py       # Settings loaded from environment / .env
│       │   ├── database.py     # Async SQLAlchemy engine + session factory
│       │   ├── security.py     # JWT creation/verification, bcrypt hashing
│       │   └── logger.py       # Structured logging setup
│       └── middleware/
│           ├── cors_handler.py
│           └── error_handler.py
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.js
    ├── pages/
    │   ├── index.tsx           # Landing / chat page
    │   ├── dashboard.tsx       # Main teacher dashboard (chat + stats)
    │   ├── documents.tsx       # Document upload & management
    │   ├── evaluation.tsx      # RAGAS metrics viewer
    │   ├── history.tsx         # Audit trail
    │   ├── question-bank.tsx   # Saved questions
    │   ├── settings.tsx        # User profile settings
    │   ├── login.tsx
    │   └── register.tsx
    ├── components/
    │   ├── Sidebar.tsx         # Folder tree + conversation list + nav
    │   ├── ChatWindow.tsx      # Message list renderer
    │   ├── ChatInput.tsx       # Prompt input + document attachment chip
    │   ├── MessageItem.tsx     # Single message with Bloom tags + feedback
    │   ├── MessageFeedback.tsx # Thumbs-up/down widget
    │   ├── DocumentUploader.tsx
    │   └── Layout.tsx
    ├── store/
    │   └── appStore.ts         # Zustand global state
    ├── lib/
    │   ├── api.ts              # Axios client + all API call wrappers
    │   └── translations.ts     # EN/ES string table
    ├── hooks/
    │   ├── useT.ts             # Translation hook
    │   └── useSubject.ts       # Subject name translation hook
    └── types/
        └── index.ts            # TypeScript type definitions
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend framework | Next.js 14 (Pages Router) | SSR-capable React framework |
| Frontend state | Zustand | Lightweight global store |
| UI styling | Tailwind CSS | Utility-first CSS |
| Backend framework | FastAPI 0.115 | Async Python API |
| AI orchestration | LangGraph | Stateful multi-agent workflow |
| LLM | Gemini 2.5 Flash via Vertex AI | Content generation + classification |
| LLM SDK | google-genai | Official Google GenAI Python SDK |
| Relational DB | PostgreSQL 16 | Primary data store |
| ORM | SQLAlchemy 2.0 (async) | Database access layer |
| Vector store | ChromaDB 0.5 | RAG chunk storage + similarity search |
| Auth | JWT (python-jose) + bcrypt | Stateless authentication |
| Real-time | SSE via sse-starlette | Token-by-token response streaming |
| PDF generation | ReportLab + PyMuPDF | Export + PDF parsing |
| DOCX | python-docx | Export + DOCX parsing |
| Containerisation | Docker + Docker Compose | One-command deployment |

---

## How Everything Works

### Content Generation Pipeline (LangGraph)

Every `/generate` request runs through a deterministic **StateGraph** defined in `langgraph_orchestrator.py`:

```
fetch_context → analyze → generate → review ─── approved ──→ build_result → END
                                         └── needs_regeneration ──→ generate (loop)
```

1. **fetch_context** — loads any attached document from the DB and pulls the user's past HITL feedback examples for this conversation
2. **analyze** (`AnalyzerAgent`) — interprets the user prompt, determines content type, difficulty level, and retrieves relevant chunks from ChromaDB via semantic search
3. **generate** (`GeneratorAgent`) — builds a detailed prompt using the analysis + RAG context, calls `LLMService.generate_with_prompt()`, returns raw content
4. **review** (`ReviewerAgent`) — scores the content (0–1) against quality criteria; if score < threshold AND attempts < `MAX_GENERATION_ATTEMPTS`, routes back to **generate** with improvement instructions; otherwise routes to **build_result**
5. **build_result** — packages the final content, Bloom taxonomy tags, review score, and attempt count into the output state

`MAX_GENERATION_ATTEMPTS = 0` (set in `config.py`) means infinite HITL retries — the loop only stops when the reviewer approves.

### RAG Pipeline

**Ingestion** (`document_ingestion_service.py`):
1. Teacher uploads a PDF, DOCX, or TXT file via `POST /documents`
2. Text is extracted (PyMuPDF for PDF, python-docx for DOCX)
3. Text is split into overlapping chunks: chunk size = 1500 chars, overlap = 12%
4. Each chunk is stored in PostgreSQL (`chunks` table) and embedded + indexed in ChromaDB
5. The subject is inferred by calling `LLMService.infer_subject()` on the first 2000 characters

**Retrieval** (`AnalyzerAgent` → `VectorService`):
1. At generation time, the user prompt is used as a ChromaDB query
2. Top-k most similar chunks are returned (cosine similarity)
3. Retrieved text is injected into the generation prompt as grounding context

### Conversation Routing

`ConversationService.process_message_and_route()` decides whether a message continues an existing conversation or starts a new one:

- **No `conversation_id`** (user clicked New Chat) → always creates a new conversation
- **`conversation_id` provided** → detects subject/topic with `MetadataAnalyzer.hybrid_detect()`:
  - No subject detected → treat as follow-up, stay in current conversation
  - Subject detected → compute `_topic_similarity()` score (0–1)
    - Score ≥ 0.45 → continue in current conversation
    - Score < 0.45 → create a new conversation under the detected subject
  - Auto-creates a named folder for the new subject if one doesn't exist

**Hybrid detection** uses two layers:
1. Keyword lookup (fast path) against a curated database of 200+ academic terms
2. LLM fallback (slow path) via Gemini when keyword confidence < 0.75

### Human-in-the-Loop (HITL)

Three feedback mechanisms:

1. **Message ratings** — thumbs-up/down on any assistant message via `POST /conversations/{id}/messages/{msg_id}/rate`. Stored in `message_ratings`.

2. **Subject reclassification** — teacher corrects the detected subject label via the three-dot menu → "Correct Subject". Calls `POST /conversations/{id}/reclassify`. The system:
   - Updates the conversation's subject and title
   - Finds or creates a folder with the corrected subject name
   - Stores a `ClassificationCorrection` record
   - Future classifications for this user inject those corrections as few-shot examples into the LLM prompt

3. **Folder moves** — dragging a conversation to a different folder calls `POST /conversations/{id}/move-folder`. If the destination folder name differs from the current subject, a `ClassificationCorrection` is also stored.

### SSE Streaming

The `/conversations/message/stream` endpoint returns an `EventSourceResponse` (sse-starlette). The async generator yields three event types:

```
data: {"type": "meta",  "conversation_id": "...", "is_new_conversation": false, ...}
data: {"type": "chunk", "content": "Hello "}
data: {"type": "chunk", "content": "world!"}
data: {"type": "done",  "message_id": "...", "bloom_tags": [...], "title": "..."}
```

Because Vertex AI buffers the full response before returning it, native streaming offers no UX benefit. Instead, `LLMService._generate_with_gemini_stream()` generates the complete response and then emits it in 25-character chunks at 20ms intervals (~500 chars/sec), producing smooth progressive rendering on the frontend.

The frontend (`dashboard.tsx`) reads the stream with `for await ... of apiClient.sendMessageStream()` and progressively updates the message in Zustand state as chunks arrive.

### RAGAS Evaluation

`evaluation_service.evaluate()` computes three metrics without extra LLM calls:

| Metric | Formula | What it measures |
|--------|---------|-----------------|
| **Answer Relevance** | `|query_tokens ∩ answer_tokens| / |query_tokens|` | Does the answer address what was asked? |
| **Faithfulness** | `|answer_tokens ∩ context_tokens| / |answer_tokens|` | Is the answer grounded in retrieved sources? |
| **Context Precision** | `|context_tokens ∩ answer_tokens| / |context_tokens|` | How focused/relevant was the retrieved context? |
| **Overall** | `faithfulness×0.40 + relevance×0.35 + precision×0.25` | Weighted composite |

When no context was retrieved (pure parametric knowledge), faithfulness and context precision default to 0.5 (neutral).

---

## API Endpoints

All endpoints are prefixed by the router. Base URL: `http://localhost:8000`

### Auth — `/auth`
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create a new teacher account |
| POST | `/auth/login` | Returns a JWT access token |
| GET | `/auth/me` | Returns current user profile |
| PUT | `/auth/me` | Update profile (name, subject, level) |

### Conversations — `/conversations`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/conversations` | List all conversations for the user |
| POST | `/conversations` | Create a conversation manually |
| GET | `/conversations/{id}` | Get a single conversation with messages |
| PUT | `/conversations/{id}` | Update title / subject / topic |
| DELETE | `/conversations/{id}` | Delete conversation and all child records |
| POST | `/conversations/message` | Send a message (non-streaming) |
| POST | `/conversations/message/stream` | Send a message with SSE streaming |
| POST | `/conversations/{id}/move-folder` | Move to a folder (stores HITL correction) |
| POST | `/conversations/{id}/reclassify` | Correct subject label (stores HITL correction) |
| POST | `/conversations/{id}/generate` | Run full LangGraph content generation |
| POST | `/conversations/{id}/refine` | Re-generate with new feedback |
| POST | `/conversations/{id}/messages/{msg_id}/rate` | Thumbs-up/down on a message |

### Documents — `/documents`
| Method | Path | Description |
|--------|------|-------------|
| POST | `/documents/upload` | Upload PDF/DOCX/TXT — triggers RAG ingestion |
| GET | `/documents` | List user's documents |
| GET | `/documents/{id}` | Get document metadata + chunks |
| DELETE | `/documents/{id}` | Delete document and its vectors |

### Folders — `/folders`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/folders` | List all folders |
| POST | `/folders` | Create a folder |
| PUT | `/folders/{id}` | Update name / color / icon |
| DELETE | `/folders/{id}` | Delete folder (moves conversations to uncategorised) |

### Evaluation — `/evaluation`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/evaluation/conversation/{id}` | RAGAS metrics for all messages in a conversation |
| GET | `/evaluation/summary` | Aggregate quality stats across all conversations |

### Audit — `/audit`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/audit/decisions` | Agent decision records (generation history) |
| GET | `/audit/corrections` | Classification correction history |

### Export — `/export`
| Method | Path | Description |
|--------|------|-------------|
| POST | `/export/pdf` | Export content as PDF (ReportLab) |
| POST | `/export/docx` | Export content as DOCX |

### Question Bank — `/questions`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/questions` | List saved questions (filterable by subject/topic/bloom) |
| POST | `/questions` | Save a question from a generated exam |
| DELETE | `/questions/{id}` | Delete a question |

### Other
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check — returns `{"status": "healthy"}` |

---

## Database Schema

All tables use UUIDs as primary keys. Key relationships:

```
users
 ├── folders (user_id FK)
 │    └── conversations (folder_id FK, nullable)
 ├── conversations (user_id FK)
 │    ├── messages (conversation_id FK)
 │    │    └── message_ratings (message_id FK)
 │    ├── generated_contents (conversation_id FK)
 │    │    └── feedback_records (content_id FK)
 │    ├── documents (conversation_id FK, nullable)
 │    │    └── chunks (document_id FK)
 │    ├── agent_decision_records (conversation_id FK)
 │    ├── classification_corrections (conversation_id FK)
 │    └── topic_change_logs (conversation_id FK)
 ├── documents (user_id FK)
 ├── questions (user_id FK)
 ├── message_ratings (user_id FK)
 └── classification_corrections (user_id FK)
```

Notable columns:
- `conversations.locked_topic` — topic used for change detection
- `conversations.primary_subject / primary_topic` — auto-detected from first message
- `messages.detection_method` — `"keywords"`, `"llm"`, or `"document"`
- `messages.detection_confidence` — 0.0–1.0
- `generated_contents.total_regeneration_attempts` — HITL loop counter
- `generated_contents.review_score` — last ReviewerAgent score
- `classification_corrections.sample_prompt` — first 200 chars of the message that triggered the correction (used as few-shot example)

---

## Configuration

All settings are in `backend/app/core/config.py` and read from environment variables (with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://user:password@localhost/academic_generator` | PostgreSQL connection string |
| `SECRET_KEY` | `your-secret-key-change-this` | JWT signing key — **change in production** |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT lifetime |
| `GOOGLE_CLOUD_PROJECT` | `alejandria-488623` | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Vertex AI region |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model used for all LLM calls |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Path to service account JSON |
| `CHROMA_DIR` | `./chromadb_data` | ChromaDB persistence directory |
| `MAX_DOCUMENT_SIZE` | `52428800` (50 MB) | Upload size limit |
| `ALLOWED_FILE_TYPES` | `["pdf", "docx", "txt"]` | Accepted document formats |
| `CHUNK_SIZE` | `1500` | RAG chunk size in characters |
| `CHUNK_OVERLAP` | `0.12` | 12% overlap between adjacent chunks |
| `MAX_GENERATION_ATTEMPTS` | `0` | Max LangGraph review loops (0 = unlimited) |
| `GENERATION_TIMEOUT` | `60` | LLM call timeout in seconds |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed frontend origins |

---

## Setup & Running

### Prerequisites
- Docker Desktop (Windows/macOS) or Docker Engine + Docker Compose (Linux)
- A Google Cloud service account JSON with Vertex AI permissions
- Place the credentials file at `backend/credentials.json`

### Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd Proyecto_202610

# 2. Copy and edit the environment file (optional — defaults work for local dev)
cp .env.example .env

# 3. Start everything
docker-compose up --build

# The first run builds the images and downloads dependencies (~3–5 min).
# Subsequent runs start in seconds.
```

Services after startup:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs
- API docs (ReDoc): http://localhost:8000/redoc

### Stopping

```bash
# Stop containers, keep all data (PostgreSQL + ChromaDB volumes)
docker-compose down

# Stop AND wipe all data (use when DB schema changes)
docker-compose down -v
```

### First-time use

1. Open http://localhost:3000
2. Click **Register** and create a teacher account
3. Start a chat or upload a document via the Documents tab
4. Use the three-dot menu on any conversation to correct its subject label or move it to a folder

---

## Google Cloud / Vertex AI Connection

The backend authenticates with Google Cloud using **Application Default Credentials (ADC)** via a service account JSON file:

```
docker-compose.yml sets:
  GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json

./backend/credentials.json  ←  volume-mounted into the container at /app/credentials.json
```

`LLMService._get_client()` initialises the `google.genai.Client` once (lazy singleton):

```python
client = genai.Client(
    vertexai=True,
    project=settings.GOOGLE_CLOUD_PROJECT,   # "alejandria-488623"
    location=settings.GOOGLE_CLOUD_LOCATION, # "us-central1"
)
```

All LLM calls go through `client.aio.models.generate_content(model=settings.GEMINI_MODEL, ...)` using the async interface. The service account must have the **Vertex AI User** role on the project.

ChromaDB uses its own built-in embedding model (no external call) — it runs entirely in-process inside the backend container and persists data to the `chromadb_data` Docker volume.
