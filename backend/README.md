# Academic Content Generator - Backend

FastAPI backend for the academic content generation system with LangGraph orchestration and Gemini/GPT-4o integration.

## Tech Stack
- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Vector DB**: ChromaDB
- **LLM Orchestration**: LangGraph
- **LLM Providers**: Google Gemini 1.5 Pro / OpenAI GPT-4o
- **Authentication**: JWT

## Features
- RESTful API for content generation
- User authentication and authorization
- Conversation management with feedback tracking
- Content generation with streaming support
- Vector database for source retrieval
- Human-in-the-loop feedback mechanism
- Audit trail for all content iterations

## Installation

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Google Gemini API key or OpenAI API key

### Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/Scripts/activate  # Windows
# or
source venv/bin/activate  # macOS/Linux
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
```

4. Configure your API keys in `.env`:
```env
GOOGLE_API_KEY=your_key_here
# or
OPENAI_API_KEY=your_key_here
```

5. Set up database:
```bash
# Create database manually or via docker-compose
```

6. Run migrations:
```bash
# Models are auto-created on app startup
```

## Running

### Development
```bash
uvicorn main:app --reload
```

### With Docker Compose
```bash
docker-compose up
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user

### Conversations
- `GET /conversations` - List all conversations
- `GET /conversations/{id}` - Get specific conversation
- `POST /conversations` - Create new conversation
- `PUT /conversations/{id}` - Update conversation
- `DELETE /conversations/{id}` - Delete conversation

### Content Generation
- `POST /conversations/{id}/generate` - Generate content
- `POST /conversations/{id}/messages` - Add message
- `POST /content/{id}/feedback` - Submit feedback

## Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/academic_generator

# Authentication
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# LLM Configuration
GOOGLE_API_KEY=your_google_key_here
GEMINI_MODEL=gemini-1.5-pro

OPENAI_API_KEY=your_openai_key_here
GPT_MODEL=gpt-4o

LLM_PROVIDER=gemini  # or "openai"

# ChromaDB
CHROMA_DIR=./chromadb_data

# Debug
DEBUG=False
```

## Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── auth.py
│   │   └── conversations.py
│   ├── core/             # Core configuration
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   │   ├── user_service.py
│   │   ├── llm_service.py
│   │   └── vector_service.py
│   └── orchestration/    # LangGraph flows
├── tests/                # Test files
├── main.py              # FastAPI application entry
├── requirements.txt     # Python dependencies
└── Dockerfile
```

## Using Google Cloud Platform

With your $50 Google Cloud coupon, you can deploy this application:

1. Create a GCP project
2. Enable required APIs:
   - Gemini 1.5 Pro API
   - Cloud SQL (PostgreSQL)
   - Cloud Run for backend
   - Cloud Storage for files

3. Create PostgreSQL instance:
```bash
gcloud sql instances create academic-generator --database-version=POSTGRES_16
```

4. Create database:
```bash
gcloud sql databases create academic_generator \
  --instance=academic-generator
```

5. Deploy to Cloud Run:
```bash
gcloud run deploy academic-generator \
  --source . \
  --platform managed \
  --region us-central1
```

## Development

### Run tests
```bash
pytest tests/
```

### Lint
```bash
flake8 app/
black app/
```

## License

Proprietary - Academic use only
