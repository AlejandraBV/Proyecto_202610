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
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
    subject: Optional[str] = None
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
    subject: Optional[str] = None
    topic: Optional[str] = None
    detected_content_type: Optional[str] = None
    detection_confidence: Optional[float] = None
    detection_method: Optional[str] = None
    document_id: Optional[str] = None

    class Config:
        from_attributes = True


# Intelligent message routing (no dropdowns required)
class MessageRequest(BaseModel):
    user_prompt: str
    conversation_id: Optional[str] = None
    document_id: Optional[str] = None
    difficulty: Optional[str] = None


class BloomTag(BaseModel):
    """Single entry in the Bloom's taxonomy distribution for a generated response."""
    level: str           # "Remember" | "Understand" | "Apply" | "Analyze" | "Evaluate" | "Create"
    count: int           # number of questions/items at this level
    color: str           # tailwind color name used for badge rendering


class RoutedMessageResponse(BaseModel):
    conversation_id: str
    is_new_conversation: bool
    subject: Optional[str] = None
    topic: Optional[str] = None
    content_type: Optional[str] = None
    confidence: float = 0.0
    detection_method: Optional[str] = None
    content: str
    title: Optional[str] = None
    bloom_tags: Optional[List[BloomTag]] = None   # Bloom's taxonomy distribution


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
    primary_subject: Optional[str] = None
    primary_topic: Optional[str] = None
    all_topics: Optional[str] = None
    folder_id: Optional[str] = None
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
    bloom_tags: Optional[List[BloomTag]] = None


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


# Folder Schemas - para organizar conversaciones por tema
# HITL Schemas

class MessageRateRequest(BaseModel):
    """Rate a single assistant message: +1 (helpful) or -1 (not helpful)."""
    rating: int          # must be +1 or -1
    feedback_text: Optional[str] = None


class MessageRateResponse(BaseModel):
    rating_id: str
    message_id: str
    rating: int
    recorded: bool


class ReclassifyRequest(BaseModel):
    """Correct the AI-inferred subject of a conversation."""
    subject: str                      # user's corrected subject
    folder_id: Optional[str] = None   # explicit folder; if omitted, auto-resolve


class ReclassifyResponse(BaseModel):
    conversation_id: str
    old_subject: Optional[str] = None
    new_subject: str
    folder_id: Optional[str] = None
    title: str


class RefineRequest(BaseModel):
    """
    Body for the HITL message-refine endpoint.

    The professor edits the AI's output directly, then sends both versions.
    The LLM is asked to produce a final polished version that:
      - Keeps all intentional changes the professor made
      - Preserves academic formatting and quality
    """
    edited_content: str   # professor's edited version of the message


class RefineResponse(BaseModel):
    """New assistant message produced by the refinement loop."""
    message_id: str
    conversation_id: str
    content: str
    content_type: Optional[str] = None
    timestamp: str


class FolderBase(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#3B82F6"
    icon: str = "folder"
    is_default: bool = False


class FolderCreate(FolderBase):
    pass


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    order: Optional[int] = None
    is_default: Optional[bool] = None


class FolderResponse(FolderBase):
    id: str
    user_id: str
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
