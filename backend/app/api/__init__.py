# API init
from app.api.auth import router as auth_router
from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router

__all__ = ["auth_router", "conversations_router", "documents_router"]
