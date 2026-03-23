from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str
    institution: Optional[str] = None
    subject: Optional[str] = None
    level: Optional[str] = "university"


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Auth Schemas
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None


# Document Schemas
class DocumentUpload(BaseModel):
    subject: str
    topic: Optional[str] = None
    description: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    chunks_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Message Schemas
class MessageCreate(BaseModel):
    role: str
    content: str
    content_type: Optional[str] = None


class MessageResponse(MessageCreate):
    id: str
    timestamp: datetime

    class Config:
        from_attributes = True


# Feedback Schemas
class FeedbackRecordResponse(BaseModel):
    id: str
    feedback: str
    status: str
    editor_name: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class GeneratedContentResponse(BaseModel):
    id: str
    content_type: str
    title: str
    content: str
    feedback: Optional[str] = None
    version: int
    created_at: datetime
    updated_at: datetime
    feedback_records: List[FeedbackRecordResponse] = []

    class Config:
        from_attributes = True


# Conversation Schemas
class ConversationCreate(BaseModel):
    title: str
    subject: Optional[str] = None
    topic: Optional[str] = None


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    last_edited: Optional[datetime] = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_edited: Optional[datetime] = None
    messages: List[MessageResponse] = []
    generated_contents: List[GeneratedContentResponse] = []

    class Config:
        from_attributes = True


# LLM Request/Response Schemas
class LLMRequest(BaseModel):
    content_type: str  # "exam", "slideshow", "guide", "question", "text"
    subject: str
    topic: str
    level: str  # "beginner", "intermediate", "advanced", "expert"
    additional_context: Optional[str] = None
    previous_feedback: Optional[str] = None
    include_document: bool = False
    document_id: Optional[str] = None


class LLMResponse(BaseModel):
    generated_content: str
    content_type: str
    suggested_title: str
    confidence: float


# Feedback Submit Schema
class FeedbackSubmit(BaseModel):
    feedback: str
    status: str  # "approved", "needs_revision", "rejected"
    editor_name: Optional[str] = None
    request_regeneration: bool = False


class RegenerationRequest(BaseModel):
    feedback_text: str
    content_id: str
    include_document: bool = False
    document_id: Optional[str] = None


# RAG & Analysis Schemas
class DocumentAnalysis(BaseModel):
    document_id: str
    chunks_created: int
    chunk_ids: List[str]
    subject: str
    topic: Optional[str] = None
    status: str


class GenerationRequest(BaseModel):
    content_type: str
    subject: str
    topic: str
    level: str
    user_prompt: str
    include_document: bool = False
    document_id: Optional[str] = None
    use_approved_examples: bool = True


class GenerationResponse(BaseModel):
    conversation_id: str
    content: str
    content_type: str
    title: Optional[str] = None
    version: int
    status: str
    review_score: float
    generation_attempts: int
    analysis: Optional[Dict[str, Any]] = None
    review: Optional[Dict[str, Any]] = None


# Vector Search Schemas
class VectorSearchRequest(BaseModel):
    query: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    top_k: int = 5


class VectorSearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    relevance_score: Optional[float] = None
