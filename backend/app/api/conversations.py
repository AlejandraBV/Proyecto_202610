"""
Conversations API - CRUD and content generation endpoints
"""
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.schemas import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    MessageCreate, MessageResponse,
    GeneratedContentResponse, GenerationRequest, GenerationResponse,
    FeedbackSubmit, RegenerationRequest,
)
from app.models.models import (
    Conversation, Message, GeneratedContent, FeedbackRecord,
)
from app.orchestration.content_orchestrator import ContentOrchestrator
from app.agents.feedback_agent import FeedbackAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_current_user_id(authorization: Optional[str]) -> str:
    """Extract user ID from Bearer token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token_str = authorization.removeprefix("Bearer ")
    payload = decode_token(token_str)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return str(user_id)


# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ConversationResponse])
async def get_conversations(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for the authenticated user"""
    user_id = get_current_user_id(authorization)

    result = await db.execute(
        select(Conversation)
        .filter(Conversation.user_id == user_id)
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.generated_contents),
        )
    )
    return result.scalars().all()


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific conversation by ID"""
    user_id = get_current_user_id(authorization)

    result = await db.execute(
        select(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.generated_contents),
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation"""
    user_id = get_current_user_id(authorization)

    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=data.title,
        subject=data.subject,
        topic=data.topic,
    )

    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Update a conversation"""
    user_id = get_current_user_id(authorization)

    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if data.title is not None:
        conversation.title = data.title
    if data.subject is not None:
        conversation.subject = data.subject
    if data.topic is not None:
        conversation.topic = data.topic
    if data.last_edited is not None:
        conversation.last_edited = data.last_edited

    conversation.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(conversation)

    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation"""
    user_id = get_current_user_id(authorization)

    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()


# ---------------------------------------------------------------------------
# Content generation
# ---------------------------------------------------------------------------

@router.post("/{conversation_id}/generate", response_model=GenerationResponse)
async def generate_content(
    conversation_id: str,
    request: GenerationRequest,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate academic content using the RAG + Agent pipeline.

    Workflow:
    1. Analyzer Agent: Analyzes prompt and retrieves RAG context
    2. Generator Agent: Generates content with LLM + context
    3. Reviewer Agent: Validates quality; loops up to MAX_GENERATION_ATTEMPTS times
    4. Stores result in DB and returns to user
    """
    user_id = get_current_user_id(authorization)

    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        generation_result = await ContentOrchestrator.generate_with_rag_and_agents(
            conversation_id=conversation_id,
            user_prompt=request.user_prompt,
            subject=request.subject,
            topic=request.topic,
            level=request.level,
            user_id=user_id,
            db=db,
        )

        content_type = generation_result.get("content_type", request.content_type)
        title = f"{content_type.title()} on {request.topic}"

        generated_content = GeneratedContent(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            content_type=content_type,
            title=title,
            content=generation_result["content"],
            version=generation_result.get("version", 1),
        )

        user_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=request.user_prompt,
        )
        assistant_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="assistant",
            content=generation_result["content"],
            content_type=content_type,
        )

        db.add(generated_content)
        db.add(user_message)
        db.add(assistant_message)
        conversation.last_edited = datetime.utcnow()
        conversation.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(generated_content)

        return GenerationResponse(
            conversation_id=conversation_id,
            content=generation_result["content"],
            content_type=content_type,
            title=title,
            version=generation_result.get("version", 1),
            status=generation_result.get("status", "generated"),
            review_score=generation_result.get("review_score", 0.75),
            generation_attempts=generation_result.get("generation_attempts", 1),
            analysis=generation_result.get("analysis"),
            review=generation_result.get("review"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating content for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a conversation"""
    user_id = get_current_user_id(authorization)

    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_result = await db.execute(
        select(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)
    )
    return msg_result.scalars().all()


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: str,
    message: MessageCreate,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Add a message to a conversation"""
    user_id = get_current_user_id(authorization)

    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=message.role,
        content=message.content,
        content_type=message.content_type,
    )

    db.add(msg)
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(msg)

    return msg


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

@router.post("/{conversation_id}/content/{content_id}/feedback")
async def submit_feedback(
    conversation_id: str,
    content_id: str,
    feedback_data: FeedbackSubmit,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Submit teacher feedback on generated content"""
    user_id = get_current_user_id(authorization)

    result = await db.execute(
        select(GeneratedContent)
        .filter(GeneratedContent.id == content_id)
        .join(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    feedback_record = FeedbackRecord(
        id=str(uuid.uuid4()),
        content_id=content_id,
        feedback=feedback_data.feedback,
        status=feedback_data.status,
        editor_name=feedback_data.editor_name,
    )

    db.add(feedback_record)
    content.feedback = feedback_data.feedback
    content.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(feedback_record)

    feedback_result = await FeedbackAgent.process_feedback(
        content_id=content_id,
        feedback_text=feedback_data.feedback,
        status=feedback_data.status,
        editor_name=feedback_data.editor_name or "Anonymous",
        db=db,
    )

    return {
        "detail": "Feedback submitted",
        "feedback_id": feedback_record.id,
        "next_action": feedback_result.get("next_action"),
    }


# ---------------------------------------------------------------------------
# Regeneration with feedback
# ---------------------------------------------------------------------------

@router.post("/{conversation_id}/regenerate", response_model=GenerationResponse)
async def regenerate_with_feedback(
    conversation_id: str,
    request: RegenerationRequest,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate content incorporating teacher feedback"""
    user_id = get_current_user_id(authorization)

    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    original = await db.execute(
        select(GeneratedContent).filter(
            GeneratedContent.id == request.content_id,
        )
    )
    original_content = original.scalar_one_or_none()

    if not original_content:
        raise HTTPException(status_code=404, detail="Original content not found")

    try:
        regeneration_prompt = await FeedbackAgent.get_regeneration_instructions(
            feedback_text=request.feedback_text,
            content=original_content.content,
        )

        generation_result = await ContentOrchestrator.generate_with_rag_and_agents(
            conversation_id=conversation_id,
            user_prompt=regeneration_prompt,
            subject=conversation.subject or "General",
            topic=conversation.topic or "General",
            level="intermediate",
            user_id=user_id,
            previous_feedback=[{"feedback": request.feedback_text}],
            db=db,
        )

        new_content = GeneratedContent(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            content_type=original_content.content_type,
            title=original_content.title,
            content=generation_result["content"],
            version=original_content.version + 1,
        )

        db.add(new_content)
        await db.commit()
        await db.refresh(new_content)

        return GenerationResponse(
            conversation_id=conversation_id,
            content=new_content.content,
            content_type=new_content.content_type,
            title=new_content.title,
            version=new_content.version,
            status="regenerated",
            review_score=generation_result.get("review_score", 0.75),
            generation_attempts=generation_result.get("generation_attempts", 1),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating content: {e}")
        raise HTTPException(status_code=500, detail=str(e))
