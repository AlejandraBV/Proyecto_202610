from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/academic_generator"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Google/Gemini
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-pro"
    
    # OpenAI
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
    MAX_GENERATION_ATTEMPTS: int = 3
    GENERATION_TIMEOUT: int = 60  # seconds
    
    # App settings
    APP_NAME: str = "Academic Content Generator"
    DEBUG: bool = False
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
