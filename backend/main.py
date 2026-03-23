"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import auth_router, conversations_router, documents_router


# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered academic content generation with RAG pipeline and human-in-the-loop feedback",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(documents_router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "features": [
            "RAG Pipeline with semantic chunking",
            "Multi-agent orchestration (Analyzer, Generator, Reviewer, Feedback)",
            "Human-in-the-loop feedback system",
            "Document ingestion (PDF, DOCX, TXT)",
            "Few-shot prompting with approved examples",
            "Streaming LLM responses",
        ]
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Academic Content Generator v2",
        "version": "2.0.0",
        "docs": "/docs",
        "description": "AI-powered educational content generation with RAG, agents, and human feedback",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
