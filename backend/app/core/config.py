from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/academic_generator"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Google Cloud / Vertex AI
    GOOGLE_CLOUD_PROJECT: str = "alejandria-488623"
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # OpenAI (optional fallback)
    OPENAI_API_KEY: Optional[str] = None
    GPT_MODEL: str = "gpt-4o"

    # LLM Choice
    LLM_PROVIDER: str = "gemini"  # "gemini" or "openai"
    
    # ChromaDB
    CHROMA_DIR: str = "./chromadb_data"
    
    # RAG & Document Processing
    MAX_DOCUMENT_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: list = ["pdf", "docx", "txt"]
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: float = 0.12  # 12% overlap as per spec
    
    # Generation
    # Set to 0 for infinite HITL retries; any positive value caps retries
    MAX_GENERATION_ATTEMPTS: int = 0
    GENERATION_TIMEOUT: int = 60  # seconds
    
    # App settings
    APP_NAME: str = "Academic Content Generator"
    DEBUG: bool = False
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
