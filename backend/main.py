"""
Main FastAPI application entry point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logger import setup_logging
from app.api import auth_router, conversations_router, documents_router
from app.api.health import router as health_router
from app.middleware.cors_handler import setup_cors
from app.middleware.error_handler import ErrorHandlerMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    setup_logging()
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered academic content generation with RAG pipeline "
        "and human-in-the-loop feedback"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# Middleware
setup_cors(app)
app.add_middleware(ErrorHandlerMiddleware)

# Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(documents_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
