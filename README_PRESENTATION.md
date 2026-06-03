# AI-Powered Academic Content Generator
### Intelligent Teaching Assistant for Higher Education
**Alejandra Bravo Vega — Universidad de los Andes, 2026**

---

## What is this app?

A web application that helps university professors generate high-quality academic content (exams, study guides, summaries, presentations) using AI. The professor uploads their course material, describes what they need, and the system generates content tailored to the subject, topic, and pedagogical level — with full human oversight at every step.

---

## Core Architecture

```
Professor (browser)
      │
      ▼
Next.js Frontend (localhost:3000)
      │  REST + SSE streaming
      ▼
FastAPI Backend (localhost:8000)
      │
      ├── PostgreSQL  ← conversations, messages, feedback, questions
      ├── ChromaDB    ← vector embeddings for RAG
      └── Google Gemini (Vertex AI) ← LLM
```

---

## Feature Overview

| Feature | What it does |
|---------|-------------|
| **RAG Pipeline** | Uploads PDF/DOCX/TXT → chunks → embeds → retrieves at query time |
| **LangGraph Orchestration** | Multi-agent pipeline with quality loop |
| **Streaming responses** | Text appears word-by-word (like ChatGPT) via SSE |
| **Bloom's Taxonomy tagging** | Every response tagged with cognitive levels |
| **HITL feedback loop** | Rate, edit, refine, reclassify — AI learns from corrections |
| **RAGAS Evaluation** | Faithfulness, answer relevance, context precision metrics |
| **Audit Trail** | Full chronological log of every human correction |
| **Export PDF/Word** | Download any generated content |
| **Question Bank** | Save, search, and reuse questions across courses |
| **Syllabus input** | Structured course outline as RAG context |
| **Folder organization** | Group conversations by subject/course |

---

## 1. RAG Pipeline (Retrieval-Augmented Generation)

When the professor uploads a document:
1. **Chunking** — Document split into ~500-token semantic chunks (PyMuPDF)
2. **Embedding** — Each chunk embedded with ChromaDB's ONNX model
3. **Storage** — Vectors stored in ChromaDB (persisted volume)
4. **Retrieval** — At query time, top-k most similar chunks retrieved by cosine similarity
5. **Injection** — Retrieved chunks injected into the LLM prompt as grounding context

This means the AI never hallucinates content from outside the course material.

---

## 2. LangGraph Multi-Agent Pipeline

The content generation uses a **LangGraph StateGraph** — a directed graph of AI agents that can loop back to improve quality.

```
fetch_context ──▶ analyze ──▶ generate ──▶ review ──┐
                                                     │
                              ◀── regenerate ────────┘ (if score < threshold)
                                                     │
                                               build_result ──▶ END
```

### Nodes (Agents)

| Node | Agent | Role |
|------|-------|------|
| `fetch_context` | — | Loads document chunks from ChromaDB |
| `analyze` | **AnalyzerAgent** | Detects content type, difficulty, retrieves RAG context |
| `generate` | **GeneratorAgent** | Calls Gemini to produce content |
| `review` | **ReviewerAgent** | Scores quality (0–1), decides approve or regenerate |
| `build_result` | **ReviewerAgent** | Tags Bloom levels, packages final response |

### The Quality Loop

The `review → generate` loop implements **automatic quality control**:
- If `quality_score < 0.7` AND `attempt < max_attempts (3)` → regenerates with improvement instructions
- If approved OR max attempts reached → delivers result
- In practice, most content is approved in **1 attempt** (score ~0.85)

### Why LangGraph?
Traditional pipelines use a `while` loop — hard to reason about, hard to extend. LangGraph makes the flow **explicit as a graph**, supports conditional edges, and is designed exactly for this "generate → validate → maybe loop" pattern.

---

## 3. Bloom's Taxonomy Classification

Every AI response is automatically analyzed and tagged with **Bloom's Taxonomy** cognitive levels (Anderson & Krathwohl revised taxonomy):

| Level | Color | Keywords detected |
|-------|-------|-------------------|
| **Remember** | 🟢 Green | define, list, recall, identify, name |
| **Understand** | 🔵 Blue | explain, describe, summarize, classify |
| **Apply** | 🟡 Yellow | solve, calculate, use, demonstrate |
| **Analyze** | 🟠 Orange | compare, differentiate, examine, break down |
| **Evaluate** | 🔴 Red | assess, critique, justify, argue |
| **Create** | 🟣 Purple | design, construct, propose, formulate |

The badges appear below every assistant message in the chat. This directly fulfills the thesis proposal's requirement to *"validar y clasificar por niveles de complejidad"*.

---

## 4. Streaming Responses (SSE)

Content streams word-by-word using **Server-Sent Events (SSE)**:

```
Backend                           Frontend
  │                                  │
  │── data: {"type":"meta", ...} ──▶ │  (sets up conversation)
  │── data: {"type":"chunk","content":"The "} ──▶ │
  │── data: {"type":"chunk","content":"exam "} ──▶ │  (appends each word)
  │── data: {"type":"chunk","content":"covers "} ──▶ │
  │── data: {"type":"done","bloom_tags":[...]} ──▶ │  (saves to DB)
```

The frontend uses `fetch` + `ReadableStream` (async generator) — no polling, no waiting for full response.

---

## 5. Human-in-the-Loop (HITL) Feedback

The system collects three types of human feedback that improve future outputs:

### 5a. Message Rating (👍)
Professor rates a response as helpful. Stored in `MessageRating` table.

### 5b. Edit & Refine
Professor edits the generated content → system sends the original + edited version back to Gemini → produces a refined version that learns the professor's style.

### 5c. Classification Correction
If the AI incorrectly identifies the subject (e.g., calls "Geohazards" → "General"), the professor corrects it. These corrections are stored as **few-shot examples** and injected into future classification prompts — the system learns each professor's terminology over time without retraining.

---

## 6. RAGAS-Inspired Evaluation

Each conversation can be evaluated with quality metrics inspired by the RAGAS framework:

| Metric | What it measures | Method |
|--------|-----------------|--------|
| **Faithfulness** | Are claims grounded in retrieved source chunks? | Word overlap (Jaccard similarity) between output and context |
| **Answer Relevance** | Does the output address the user's query? | Word overlap between output and query |
| **Context Precision** | Was the retrieved context actually used? | Overlap between context and final output |
| **Overall** | Weighted average | (faithfulness×0.4) + (relevance×0.35) + (precision×0.25) |

Navigate to **Evaluation** in the sidebar, select a conversation, click **Run Evaluation**.

> Note: Full RAGAS requires OpenAI embeddings for scoring. This implementation uses word-overlap as an approximation — valid for demonstrating the concept and sufficiently accurate for educational content evaluation.

---

## 7. Audit Trail

Every human intervention is logged and visible at **/history**:

- 👍 Message ratings with optional feedback text
- ✏️ AI refinements (original → edited → refined)
- 🏷️ Subject reclassifications (AI predicted X, professor corrected to Y)
- 🧠 Agent decisions (which agent ran, what score, approve/regenerate)

This provides full **traceability of the co-creation process** ("trazabilidad del proceso de co-creación") as described in the thesis proposal.

---

## 8. Export PDF / Word

Any generated message can be downloaded:
- **PDF** — Generated with ReportLab, preserves markdown formatting (bold, headings, lists)
- **Word (.docx)** — Generated with python-docx, editable by the professor

Click the **PDF** or **Word** buttons below any assistant message.

---

## 9. Question Bank

Questions extracted from generated exams can be saved, searched, and reused:
- **Auto-extract** — Click "Save to Bank" on any exam response → regex extracts numbered questions
- **Manual add** — Add any question with subject, topic, Bloom level, difficulty, answer
- **Search & filter** — By text, subject, Bloom level, difficulty
- Navigate to **Question Bank** in the sidebar

---

## 10. Structured Syllabus Input

Beyond PDF upload, professors can enter a structured course outline:
- Course name, subject, week number
- Learning objectives (one per line)
- Topics covered with Bloom level per topic
- Additional notes

This is indexed as RAG context, giving the AI precise pedagogical grounding.
Click the 📖 button in the chat input toolbar.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14, React, TypeScript, Tailwind CSS, Zustand |
| **Backend** | FastAPI (Python), SQLAlchemy async, Pydantic v2 |
| **Database** | PostgreSQL 16 |
| **Vector DB** | ChromaDB 0.5 |
| **LLM** | Google Gemini (Vertex AI) |
| **AI Framework** | LangGraph 1.2, LangChain Core 1.4 |
| **PDF export** | ReportLab 4.5 |
| **Word export** | python-docx |
| **Streaming** | sse-starlette (Server-Sent Events) |
| **Auth** | JWT (python-jose) + bcrypt |
| **Infrastructure** | Docker Compose (3 services) |

---

## Data Flow — Full Request Example

> Professor uploads "Geohazards.pdf", then asks: *"Create an intermediate exam on volcanic hazards"*

```
1. [Upload]  PDF → PyMuPDF → 8 chunks → ChromaDB embeddings

2. [Send]    POST /conversations/message/stream
             { user_prompt: "Create an intermediate exam...", document_id: "..." }

3. [Route]   ConversationService detects → Earth Sciences / Geohazards
             → Creates new conversation if topic changed

4. [LangGraph Pipeline]
   fetch_context → loads 8741 chars of PDF context
   analyze       → type=exam, difficulty=intermediate
   generate      → Gemini produces 3771-char exam with 10 questions
   review        → score=0.85, approved on attempt 1
   build_result  → Bloom tags: [Apply×3, Analyze×4, Evaluate×2, Create×1]

5. [Stream]  Content sent chunk-by-chunk via SSE → appears word-by-word in UI

6. [Save]    Message + Bloom tags saved to PostgreSQL

7. [Display] Exam shown with colored Bloom badges
             PDF/Word download buttons available
             "Save to Bank" extracts 10 questions to Question Bank
```

---

## Key Design Decisions

**Why LangGraph over a simple loop?**
Explicit graph structure makes the pipeline readable, testable, and extensible. Adding a new agent (e.g., a Plagiarism Checker node) is one `add_node` call.

**Why ChromaDB over a managed vector DB?**
Runs fully locally inside Docker — no external API keys, no cost, no data leaves the institution's infrastructure. Important for academic confidentiality.

**Why SSE over WebSockets?**
SSE is unidirectional (server → client), simpler than WebSockets for this use case, and works natively with `fetch` in modern browsers without extra libraries.

**Why approximate RAGAS?**
Full RAGAS requires OpenAI embeddings which add cost and an external dependency. Word-overlap metrics are deterministic, free, and sufficient to demonstrate the evaluation concept. The architecture is ready to swap in full RAGAS with one service change.

---

## Running the App

```bash
# 1. Copy environment file and fill in credentials
cp .env.example .env

# 2. Start everything (builds images, creates DB, starts all services)
docker-compose up --build

# 3. Open browser
http://localhost:3000

# 4. Register an account, upload a PDF, start generating!
```

**Services:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs

---

*Built with FastAPI · Next.js · LangGraph · ChromaDB · Google Gemini · PostgreSQL*

---

---

# Deep Dive: How Everything is Stored & Connected

---

## The Server — FastAPI + Uvicorn

The backend is a **FastAPI** application served by **Uvicorn** (an async Python web server).

```
docker container: academic_generator_backend
  └── uvicorn main:app --host 0.0.0.0 --port 8000 --reload
        └── FastAPI app
              ├── /auth/*          ← login, register, JWT
              ├── /conversations/* ← chat, streaming, HITL
              ├── /documents/*     ← upload, RAG, syllabus
              ├── /folders/*       ← organization
              ├── /questions/*     ← question bank
              ├── /feedback/*      ← content feedback
              ├── /conversations/{id}/audit      ← audit trail
              ├── /conversations/{id}/evaluate   ← RAGAS metrics
              └── /conversations/{id}/messages/{id}/export ← PDF/Word
```

**Why FastAPI?**
- Native async support (needed for non-blocking DB queries and streaming)
- Auto-generated API docs at `/docs` (Swagger UI)
- Pydantic v2 for request/response validation
- One of the fastest Python frameworks (comparable to Node.js)

**Authentication flow:**
1. Professor registers → password hashed with **bcrypt** → stored in DB
2. Professor logs in → FastAPI returns a **JWT token** (JSON Web Token)
3. Every subsequent request sends `Authorization: Bearer <token>` in the header
4. Backend decodes the JWT with `python-jose`, extracts the `user_id`, and uses it to scope all queries
5. Token expires after **30 minutes** (configurable in `config.py`)

---

## The Database — PostgreSQL 16

PostgreSQL stores all **structured data**: users, conversations, messages, feedback, questions, documents metadata.

### Database Schema (all tables)

```
┌──────────┐     ┌────────────────┐     ┌──────────┐
│  users   │────▶│ conversations  │────▶│ messages │
└──────────┘     └────────────────┘     └──────────┘
     │                  │                    │
     │                  ▼                    ▼
     │           ┌────────────────┐   ┌──────────────────┐
     │           │generated_conte │   │ message_ratings  │
     │           └────────────────┘   └──────────────────┘
     │                  │
     │                  ▼
     │           ┌────────────────┐
     │           │ feedback_record│
     │           └────────────────┘
     │
     ├──────────▶┌──────────┐     ┌────────┐
     │           │documents │────▶│ chunks │
     │           └──────────┘     └────────┘
     │
     ├──────────▶┌─────────┐
     │           │ folders │
     │           └─────────┘
     │
     ├──────────▶┌───────────────────────┐
     │           │ classification_       │
     │           │ corrections           │
     │           └───────────────────────┘
     │
     ├──────────▶┌───────────────────────┐
     │           │ agent_decision_records│
     │           └───────────────────────┘
     │
     └──────────▶┌───────────┐
                 │ questions │
                 └───────────┘
```

### What each table stores

| Table | What it saves |
|-------|--------------|
| `users` | email, hashed_password, name, institution, subject, level |
| `folders` | name, color, icon — for organizing conversations by course |
| `conversations` | title, subject, topic, folder_id, all_topics (JSON), timestamps |
| `messages` | role (user/assistant), content (full text), detected subject/topic, content_type, confidence, detection_method, document_id |
| `generated_contents` | content_type, full generated text, feedback, version number, review_score |
| `feedback_records` | feedback text, status (approved/needs_revision/rejected), editor_name |
| `documents` | filename, file_type, original_content (full text), subject, chunks_count, vector_index_ids (JSON) |
| `chunks` | individual text chunks from documents, chunk_index, vector_id (ChromaDB reference) |
| `agent_decision_records` | agent_name, decision, reasoning, quality_score, iteration |
| `message_ratings` | message_id, user_id, rating (+1/-1), feedback_text |
| `classification_corrections` | original_subject, corrected_subject, sample_prompt (for few-shot learning) |
| `questions` | content, answer, question_type, subject, topic, bloom_level, difficulty, tags, times_used |
| `topic_change_logs` | old_topic, new_topic, confidence, whether new chat was auto-created |

### How the DB connection works

```python
# backend/app/core/database.py
DATABASE_URL = "postgresql+asyncpg://user:password@postgres:5432/academic_generator"

# SQLAlchemy async engine — non-blocking queries
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession)

# On app startup (lifespan):
await Base.metadata.create_all(engine)   # creates all tables if they don't exist
```

- Uses **SQLAlchemy 2.0** with full async support (`AsyncSession`)
- Queries use `await db.execute(select(Model).where(...))` — never blocks the event loop
- The `postgres` hostname resolves inside Docker's internal network
- Data persists in a Docker **named volume** (`postgres_data`) — survives container restarts

---

## The Vector Database — ChromaDB

ChromaDB stores **document embeddings** for semantic search (RAG).

```
┌─────────────────────────────────────────────────────┐
│  ChromaDB (runs inside the backend container)        │
│                                                       │
│  Collection: "documents"                              │
│  ┌─────────────────────────────────────────────┐     │
│  │ vector_id: "abc123"                          │     │
│  │ embedding: [0.23, -0.11, 0.87, ...]  ◀─────────── chunk text embedded │
│  │ metadata: { doc_id, chunk_index, user_id }  │     │
│  │ document: "Volcanic hazards include lava..." │     │
│  └─────────────────────────────────────────────┘     │
│  ... (one entry per chunk across all documents)       │
└─────────────────────────────────────────────────────┘
        │
        └── Persisted to Docker volume: chromadb_data/
```

**How embeddings are created:**
ChromaDB uses a local **ONNX embedding model** (downloaded once on first run from S3, then cached). No external API needed for embeddings.

**How retrieval works at query time:**
```python
# 1. Embed the user's query with the same model
# 2. Find the top-k chunks with highest cosine similarity
results = collection.query(
    query_texts=["What are the main volcanic hazards?"],
    n_results=5,
    where={"user_id": current_user_id}   # scoped per professor
)
# 3. Return the chunk texts → injected into the LLM prompt
```

**Separation of concerns:**
- **PostgreSQL** stores the chunk text and metadata (for display, audit, debugging)
- **ChromaDB** stores the vectors (for fast similarity search)
- They're linked by `vector_id` in the `chunks` table

---

## The LLM — Google Gemini via Vertex AI

The app uses **Google Gemini 2.5 Flash** accessed through Vertex AI (Google Cloud).

```
backend container
      │
      │  google-genai SDK
      ▼
Google Cloud Vertex AI (us-central1)
      │
      ▼
Gemini 2.5 Flash model
```

### Connection setup

```python
# config.py
GOOGLE_CLOUD_PROJECT = "alejandria-488623"
GOOGLE_CLOUD_LOCATION = "us-central1"
GEMINI_MODEL = "gemini-2.5-flash"

# Authenticated via:
GOOGLE_APPLICATION_CREDENTIALS = "/app/credentials.json"  # service account key
```

The backend mounts `credentials.json` (a Google Cloud service account key file) into the container. The `google-genai` SDK automatically picks it up and authenticates all requests to Vertex AI.

### Regular (non-streaming) call
```python
client = genai.Client(vertexai=True, project=..., location=...)
response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
return response.text
```

### Streaming call (for word-by-word UI)
```python
async for chunk in client.models.generate_content_stream(model=GEMINI_MODEL, contents=prompt):
    yield chunk.text   # each chunk is a few words → sent via SSE to frontend
```

### Why Gemini 2.5 Flash?
- **Fast** — "Flash" variant optimized for speed over raw capability
- **Long context** — handles large documents and complex prompts
- **Vertex AI** — data stays within Google Cloud (important for institutional use)
- **Optional fallback** — config supports `LLM_PROVIDER=openai` to switch to GPT-4o

---

## How a Document Gets Stored — Step by Step

```
Professor uploads "Geohazards.pdf"
          │
          ▼
1. [FastAPI] POST /documents/upload
   - Receives multipart form-data
   - Saves metadata to PostgreSQL: documents table
     { id, user_id, filename="Geohazards.pdf", file_type="pdf" }

2. [PyMuPDF] Extracts raw text from PDF
   - "Geohazards are natural hazards arising from..."
   - Full text stored in documents.original_content

3. [Chunking] Text split into chunks
   - chunk_size = 1500 characters, overlap = 12%
   - 8 chunks created for this document
   - Each chunk saved to chunks table in PostgreSQL
     { id, document_id, chunk_index, text, vector_id }

4. [ChromaDB] Each chunk embedded + stored as vector
   - ONNX model converts text → 384-dimensional float vector
   - Stored with metadata: { doc_id, user_id, chunk_index }
   - vector_id written back to the chunks.vector_id column

5. [Response] Returns { document_id, chunks_count: 8 }
   - Frontend sets pendingDocument = { id, filename }
   - Next message will include this document_id
```

---

## How a Message Gets Saved — Step by Step

```
Professor sends: "Create an exam on volcanic hazards"
          │
          ▼
1. [FastAPI] POST /conversations/message/stream

2. [ConversationService] Topic detection
   - Keyword scan: "volcanic", "hazards" → Earth Sciences match
   - If confidence < 0.7 → calls Gemini to classify (hybrid approach)
   - Determines: subject="Earth Sciences", topic="Geohazards"
   - Checks: same as current conversation topic? YES → reuse conv
                                                  NO  → create new conv

3. [PostgreSQL] Save user message
   INSERT INTO messages (id, conversation_id, role="user",
     content="Create an exam...", subject, topic, document_id)

4. [SSE] Emit meta event → frontend creates streaming placeholder

5. [LangGraph] Run generation pipeline (see Section 2)

6. [PostgreSQL] Save assistant message
   INSERT INTO messages (id, conversation_id, role="assistant",
     content="<full exam text>", content_type="exam", subject, topic)
   UPDATE conversations SET updated_at=now(), last_edited=now()

7. [SSE] Emit done event with message_id + bloom_tags
   → Frontend replaces placeholder with final message
   → Bloom badges rendered
   → Clock on conversation = last_edited timestamp
```

---

## Docker: How the Three Services Talk to Each Other

```
┌─────────────────────────────────────────────────────────┐
│  Docker Compose — academic_network (bridge network)      │
│                                                           │
│  ┌──────────────┐   HTTP :3000   ┌──────────────────┐    │
│  │   frontend   │◀──────────────▶│    (browser)     │    │
│  │  (Next.js)   │                └──────────────────┘    │
│  └──────┬───────┘                                        │
│         │ REST + SSE :8000                               │
│         ▼                                                 │
│  ┌──────────────┐   asyncpg :5432  ┌──────────────────┐  │
│  │   backend    │◀────────────────▶│    postgres      │  │
│  │  (FastAPI)   │                  │  (PostgreSQL 16) │  │
│  └──────────────┘                  └──────────────────┘  │
│         │                                                 │
│         │ local filesystem                                │
│         ▼                                                 │
│  ┌──────────────┐                                        │
│  │  chromadb_   │  (volume mount inside backend)         │
│  │  data/       │                                        │
│  └──────────────┘                                        │
└─────────────────────────────────────────────────────────┘
         │
         │ HTTPS (Vertex AI SDK)
         ▼
  Google Cloud us-central1
  (Gemini 2.5 Flash)
```

**Key networking facts:**
- Frontend calls backend at `http://localhost:8000` (mapped from container port)
- Backend calls PostgreSQL at `postgres:5432` — `postgres` resolves via Docker's internal DNS
- ChromaDB runs **inside** the backend container (not a separate service) — accessed via local filesystem
- Only Gemini calls leave the machine — everything else is local

---

## Configuration & Environment Variables

All sensitive config lives in `.env` (never committed to git):

| Variable | What it controls |
|----------|-----------------|
| `POSTGRES_USER/PASSWORD/DB` | PostgreSQL credentials |
| `SECRET_KEY` | JWT signing key (change in production!) |
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI region (us-central1) |
| `LLM_PROVIDER` | `gemini` or `openai` |
| `OPENAI_API_KEY` | Optional — only if using GPT-4o |
| `NEXT_PUBLIC_API_URL` | Backend URL seen by the browser |
| `DEBUG` | Enables SQLAlchemy query logging |

---

## Summary: Where Everything Lives

| Data | Where stored | Persisted? |
|------|-------------|-----------|
| User accounts & passwords | PostgreSQL `users` | ✅ Permanent |
| Conversations & messages | PostgreSQL | ✅ Permanent |
| Feedback & ratings | PostgreSQL | ✅ Permanent |
| Question bank | PostgreSQL | ✅ Permanent |
| Document text | PostgreSQL `documents` | ✅ Permanent |
| Document chunk vectors | ChromaDB (volume) | ✅ Permanent |
| Auth tokens (JWT) | Browser localStorage | ⏱ 30 min expiry |
| Generated content (streaming) | SSE → then PostgreSQL | ✅ Saved at end |
| Gemini API responses | Never stored raw | — |

*Built with FastAPI · Next.js · LangGraph · ChromaDB · Google Gemini · PostgreSQL*
