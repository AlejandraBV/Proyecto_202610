"""
Health check endpoints
"""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
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
        ],
    }


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Academic Content Generator v2",
        "version": "2.0.0",
        "docs": "/docs",
        "description": (
            "AI-powered educational content generation with RAG, agents, and human feedback"
        ),
    }
