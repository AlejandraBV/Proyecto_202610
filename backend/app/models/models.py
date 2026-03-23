from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    institution = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=True)
    level = Column(String(50), nullable=True, default="university")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    topic = Column(String(255), nullable=True)
    # Auto-detected primary subject/topic (mirrors subject/topic for compatibility)
    primary_subject = Column(String(255), nullable=True)
    primary_topic = Column(String(255), nullable=True)
    # JSON list of all topics discussed in this conversation
    all_topics = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_edited = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    generated_contents = relationship("GeneratedContent", back_populates="conversation", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Auto-detected metadata
    subject = Column(String(255), nullable=True)
    topic = Column(String(255), nullable=True)
    detected_content_type = Column(String(50), nullable=True)
    detection_confidence = Column(Float, default=0.0)
    detection_method = Column(String(50), nullable=True)  # "keywords", "llm", or "document"

    # Optional reference to an uploaded document
    document_id = Column(String(36), nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class GeneratedContent(Base):
    __tablename__ = "generated_contents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    content_type = Column(String(50), nullable=False)  # "exam", "slideshow", "guide", etc
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    feedback = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    # Tracks total HITL regeneration cycles (no upper limit)
    total_regeneration_attempts = Column(Integer, default=0)
    # Score from the last reviewer pass
    review_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="generated_contents")
    feedback_records = relationship("FeedbackRecord", back_populates="content", cascade="all, delete-orphan")


class FeedbackRecord(Base):
    __tablename__ = "feedback_records"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String(36), ForeignKey("generated_contents.id"), nullable=False)
    feedback = Column(Text, nullable=False)
    status = Column(String(50), nullable=False)  # "approved", "needs_revision", "rejected"
    editor_name = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    content = relationship("GeneratedContent", back_populates="feedback_records")


class Document(Base):
    """Stores documents uploaded by teachers for RAG ingestion"""
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # "pdf", "docx", "txt", "url"
    original_content = Column(Text, nullable=False)
    chunks_count = Column(Integer, default=0)
    vector_index_ids = Column(Text, nullable=True)  # JSON list of ChromaDB IDs
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    conversation = relationship("Conversation", back_populates="documents")


class Chunk(Base):
    """Stores individual text chunks from ingested documents for RAG retrieval"""
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    chunk_size = Column(Integer, default=0)
    overlap_info = Column(Text, nullable=True)
    vector_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", backref="chunks")


class AgentDecisionRecord(Base):
    """Stores decisions made by agents during content generation"""
    __tablename__ = "agent_decision_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    decision = Column(String(50), nullable=False)
    reasoning = Column(Text, nullable=True)
    quality_score = Column(Float, nullable=True)
    iteration = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", backref="agent_decisions")
