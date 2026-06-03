# 🎓 Academic Content Generator v2.0

> **AI-Powered Multi-Agent System with RAG, Human-in-the-Loop Learning, and Smart Topic Organization**

![Version](https://img.shields.io/badge/Version-2.0.0-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11+-green?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green?style=flat-square)
![Next.js](https://img.shields.io/badge/Next.js-14+-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

## ✨ Features

### 🤖 **4 Specialized AI Agents**
- **Analyzer**: Auto-detects subject, topic, content type using hybrid keyword + LLM approach
- **Generator**: Creates content with RAG context + few-shot learning from teacher feedback
- **Reviewer**: Validates quality and difficulty alignment (0-1 confidence score)
- **Feedback Agent**: Learns from teacher edits to improve future generation quality

### 📚 **Advanced RAG Pipeline**
- **Document Ingestion**: PDF/DOCX/TXT/URL support with intelligent parsing
- **Semantic Chunking**: 1500-char chunks with 12% overlap for context preservation
- **Vector Search**: ChromaDB-powered similarity matching with re-ranking
- **Few-Shot Learning**: Teacher feedback automatically becomes examples for future prompts

### 🔄 **Human-in-the-Loop (HITL) System**
- ♾️ **Infinite Regeneration Cycles**: Teachers can regenerate content indefinitely
- ✏️ **Inline Feedback**: Mark sections for improvement and get context-aware regeneration
- 📊 **Quality Scoring**: Automatic review before presenting to user (0-1 scale)
- 🎓 **Learning Loop**: Each feedback improves system performance

### 📁 **Smart Topic Organization (NEW!)**
- **Auto-Create Folders**: One folder per subject/topic automatically
- **Auto-Detect Topic Changes**: If user switches themes, create new chat automatically
- **Prevent Context Contamination**: Each topic stays isolated for better focus
- **Folder Management**: Organize, move, color-code conversations by subject

### 🎨 **Modern Web Interface**
- Built with **Next.js 14** + **TypeScript** + **Tailwind CSS**
- Real-time updates with WebSocket support
- Responsive design for mobile/tablet/desktop
- Dark mode support
- File upload with drag-and-drop

### 🔐 **Enterprise-Grade Security**
- **JWT Authentication** with 30-min tokens
- **User Isolation**: Each user sees only their data
- **PostgreSQL**: Encrypted passwords, ACID compliance
- **CORS Protection**: Configurable origin whitelist
- **Async Operations**: Non-blocking I/O throughout

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (recommended) or Docker + Docker Compose
- API key for Gemini or OpenAI

### 1-Command Setup

**Windows (PowerShell):**
```powershell
.\setup-local.ps1
# Then open http://localhost:3000
```

**Linux/Mac (Bash):**
```bash
chmod +x setup-local.sh
./setup-local.sh
# Then open http://localhost:3000
```

### Manual Setup
```bash
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
# Wait 30 seconds, then visit http://localhost:3000
```

**Create test user:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@school.edu",
    "password": "password123",
    "name": "Teacher Name",
    "subject": "Biology"
  }'
```

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│  ┌──────────────┬──────────────┬──────────────┬─────────┐   │
│  │ Folders View │ Chat List    │ Chat Window  │ Upload  │   │
│  └──────────────┴──────────────┴──────────────┴─────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/REST
┌───────────────────────────┴─────────────────────────────────┐
│                      FastAPI Backend                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 4-Agent Orchestration (LangGraph StateGraph)        │   │
│  │  Analyzer → Generator → Reviewer → Feedback Loop    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ RAG Pipeline: Document → Chunk → Vector → Search    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Topic Detection: Auto-create chats on topic change  │   │
│  │ Folder Management: Organize conversations by theme  │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────┬────────────────────────────┬────────────────────┘
            │                            │
        PostgreSQL              ChromaDB Vector DB
        (Conversations,         (Document Embeddings,
         Users, Feedback)        Semantic Search)
```

---

## 🔄 How It Works: Conversation Flow

```
User types message
    ↓
[Analyzer Agent]
├─ Auto-detect: subject, topic, content_type
├─ Check if topic matches locked_topic
│  ├─ YES: continue in same chat
│  └─ NO: CREATE NEW CHAT automatically
├─ Retrieve relevant document chunks (RAG)
└─ Extract requirements from prompt

    ↓
[Generator Agent]
├─ Build context from retrieved chunks
├─ Add few-shot examples from teacher feedback
├─ Call LLM (Gemini or GPT-4o)
└─ Generate content

    ↓
[Reviewer Agent]
├─ Check quality (0-1 score)
├─ Verify difficulty matches level
├─ Check requirement alignment
└─ Score >= 0.85? ─ YES → Present ✓
                  └─ NO → Ask to regenerate

    ↓
[Human Review]
teacher approves/edits/rejects
    ↓
[Feedback Agent]
├─ Extract patterns from edit
├─ Store as few-shot example
└─ Improve future generations

(Loop back to Generator if needed - infinite retries!)
```

---

## 📁 New Feature: Auto-Topic Organization

### Problem Solved
❌ **Before**: User talks about Biology → History → Math all in one chat (context contamination)

✅ **After**: 
```
User asks about Biology           → Chat A: Biology
User changes to History           → (NEW) Chat B: History auto-created
                                    Chat A stays focused on Biology
```

### How It Works

1. **First message locks the topic**
   ```
   Conversation created with locked_topic = "Photosynthesis" (Biology)
   ```

2. **System monitors for topic changes**
   ```
   Each message analyzed:
   - If new_topic ≠ locked_topic
   - AND confidence > 0.7
   → Create new conversation for new topic
   → Log the change in TopicChangeLogs
   → Move user to new chat automatically
   ```

3. **Organized in Folders by Subject**
   ```
   📚 Biology/
   ├─ Photosynthesis
   ├─ Cell Structure
   └─ Genetics
   
   🔢 Mathematics/
   ├─ Calculus
   └─ Linear Algebra
   ```

---

## 🎯 API Endpoints

### Folders
```
GET    /folders                      # List all user's folders
POST   /folders                      # Create folder
GET    /folders/{id}                 # Get folder details
PUT    /folders/{id}                 # Update folder
DELETE /folders/{id}                 # Delete folder
GET    /folders/{id}/conversations   # Get chats in folder
```

### Conversations
```
GET    /conversations                # List chats
POST   /conversations                # Create chat
GET    /conversations/{id}           # Get chat + messages
POST   /conversations/{id}/messages  # Send message (triggers pipeline)
PUT    /conversations/{id}           # Update chat
DELETE /conversations/{id}           # Delete chat
```

### Content Generation
```
POST   /conversations/{id}/regenerate      # Regenerate with feedback
GET    /feedback/learning-examples         # Get approved examples for few-shot
```

### Documents (RAG)
```
POST   /documents/upload             # Upload PDF/DOCX
GET    /documents/search             # Semantic search
DELETE /documents/{id}               # Delete document
```

### Admin
```
GET    /health                       # Health check
GET    /docs                         # Swagger UI
```

---

## ⚙️ Configuration

### Key Settings (`.env`)

```env
# LLM Provider (choose one)
LLM_PROVIDER=gemini              # Default
GOOGLE_API_KEY=sk-XXXX...

# OR

LLM_PROVIDER=openai
OPENAI_API_KEY=sk-XXXX...

# Agent Tuning
MAX_AGENT_ITERATIONS=3           # Re-ranking cycles
REVIEWER_CONFIDENCE_THRESHOLD=0.85  # Quality threshold
AGENT_TIMEOUT=60                 # Seconds per agent

# RAG Tuning
CHUNK_SIZE=1500                  # Characters
CHUNK_OVERLAP=0.12               # 12% overlap
MAX_DOCUMENT_SIZE=50_000_000     # 50MB

# Security
SECRET_KEY=change-this-in-prod
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## 📦 Project Structure

```
Proyecto_202610/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/               # Route handlers
│   │   │   ├── auth.py
│   │   │   ├── conversations.py
│   │   │   ├── documents.py
│   │   │   ├── folders.py     # NEW: Folder management
│   │   │   └── feedback.py
│   │   ├── agents/            # 4 AI agents
│   │   ├── services/          # Business logic
│   │   │   ├── llm_service.py
│   │   │   ├── rag_service.py
│   │   │   ├── document_ingestion_service.py
│   │   │   └── topic_detection_service.py  # NEW
│   │   ├── models/            # SQLAlchemy ORM
│   │   │   └── models.py      # Includes Folder model
│   │   ├── schemas/           # Pydantic validation
│   │   ├── core/              # Config, security, database
│   │   └── orchestration/      # LangGraph pipeline
│   ├── main.py                # Entry point
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # Next.js application
│   ├── components/
│   │   ├── Sidebar.tsx         # NEW: Folder tree view
│   │   ├── ChatWindow.tsx
│   │   ├── MessageList.tsx
│   │   └── ...
│   ├── pages/
│   │   ├── index.tsx
│   │   └── dashboard.tsx
│   ├── lib/
│   │   └── api.ts              # Updated with folder endpoints
│   ├── types/
│   │   └── index.ts            # NEW types: Folder, TopicChangeLog
│   ├── store/
│   │   └── appStore.ts         # Zustand store
│   └── package.json
│
├── docker-compose.yml          # 5-service orchestration
├── .env.example               # Configuration template
├── setup-local.sh             # Linux/Mac setup
├── setup-local.ps1            # Windows setup
├── DEPLOYMENT_GUIDE.md        # Complete deployment docs
└── README.md                  # This file

```

---

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8000/health
# {"status": "healthy", "version": "2.0.0"}
```

### API Documentation
```
http://localhost:8000/docs       (Swagger UI)
http://localhost:8000/redoc      (ReDoc)
```

### Integration Tests
```bash
cd backend
pytest tests/test_rag_integration.py -v
```

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 in use | Change `BACKEND_PORT` in `.env` |
| API key invalid | Update `.env` and run `docker-compose restart backend` |
| Database connection error | Ensure PostgreSQL is healthy: `docker-compose logs postgres` |
| Frontend won't load | Check API URL in `.env`: `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| Out of memory | Increase Docker resources in Desktop settings |

---

## 📚 Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete local & cloud deployment instructions
- **[ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md)** - Deep dive into system design
- **[backend/README.md](backend/README.md)** - Backend-specific documentation
- **[frontend/README.md](frontend/README.md)** - Frontend-specific documentation
- **[Propuesta_202610.pdf](Propuesta_202610.pdf)** - Original specification (Spanish)

---

## 🔐 Security

- ✅ JWT authentication with expiration
- ✅ Password hashing (bcrypt)
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ XSS protection (React + Next.js)
- ✅ CORS validation
- ✅ Rate limiting (configurable)
- ✅ User data isolation

**For production:** Change `SECRET_KEY`, use HTTPS, add rate limiting, enable HTTPS-only cookies.

---

## 📈 Performance

- ⚡ **Async/Await** throughout backend (no blocking I/O)
- ⚡ **Vector caching** for frequently searched chunks
- ⚡ **Incremental feedback** prevents regenerating unchanged content
- ⚡ **Parallel agent execution** where possible (via LangGraph)
- ⚡ **Response streaming** for long generations

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Open pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 📞 Support

- 📧 Email: support@academicgenerator.edu
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions
- 📖 Docs: Full documentation in `DEPLOYMENT_GUIDE.md`

---

## 🎉 Acknowledgments

Built with ❤️ for educators using:
- **FastAPI** - Fast, modern Python web framework
- **Next.js** - React framework for production
- **LangGraph** - Agentic orchestration
- **ChromaDB** - Vector database
- **PostgreSQL** - Enterprise database
- **OpenAI/Google** - LLM providers

---

**Academic Content Generator v2.0**  
*Making quality educational content generation accessible to every teacher*  
2024 © MIT License
