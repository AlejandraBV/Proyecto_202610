"""
Conversations API - CRUD and content generation endpoints
"""
import json
import uuid
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete as sql_delete
from sqlalchemy.orm import selectinload

from app.core.database import get_db, async_session
from app.core.security import decode_token
from app.schemas import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    MessageCreate, MessageResponse, MessageRequest, RoutedMessageResponse,
    GeneratedContentResponse, GenerationRequest, GenerationResponse,
    FeedbackSubmit, RegenerationRequest,
    MessageRateRequest, MessageRateResponse,
    ReclassifyRequest, ReclassifyResponse,
    RefineRequest, RefineResponse,
    BloomTag,
)
from app.models.models import (
    Conversation, Message, GeneratedContent, FeedbackRecord,
    MessageRating, ClassificationCorrection, Document,
    AgentDecisionRecord, TopicChangeLog, Chunk,
)
from app.orchestration.content_orchestrator import ContentOrchestrator
from app.agents.feedback_agent import FeedbackAgent
from app.services.conversation_service import ConversationService

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


@router.post("/{conversation_id}/move-folder")
async def move_conversation_to_folder(
    conversation_id: str,
    data: dict,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Move a conversation to a different folder (or remove from folder if folder_id is null)"""
    from app.models.models import Folder
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

    folder_id = data.get("folder_id")
    folder_name = None
    if folder_id:
        # Verify folder belongs to this user
        folder_result = await db.execute(
            select(Folder).filter(
                Folder.id == folder_id,
                Folder.user_id == user_id,
            )
        )
        folder_obj = folder_result.scalar_one_or_none()
        if not folder_obj:
            raise HTTPException(status_code=404, detail="Folder not found")
        folder_name = folder_obj.name

    conversation.folder_id = folder_id
    conversation.updated_at = datetime.utcnow()

    # Store a ClassificationCorrection so the system learns from manual folder moves
    if folder_name and folder_name != conversation.subject:
        correction = ClassificationCorrection(
            user_id=user_id,
            conversation_id=conversation_id,
            original_subject=conversation.subject,
            corrected_subject=folder_name,
            sample_prompt=None,
        )
        db.add(correction)

    await db.commit()
    return {"detail": "Conversation moved", "conversation_id": conversation_id, "folder_id": folder_id}


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

    # Delete FK-constrained child records that don't have DB-level ON DELETE CASCADE
    # 1. Message ratings (FK → messages.id, no cascade)
    msg_ids_subq = select(Message.id).where(Message.conversation_id == conversation_id)
    await db.execute(sql_delete(MessageRating).where(MessageRating.message_id.in_(msg_ids_subq)))

    # 2. Feedback records (FK → generated_contents.id, no cascade)
    gc_ids_subq = select(GeneratedContent.id).where(GeneratedContent.conversation_id == conversation_id)
    await db.execute(sql_delete(FeedbackRecord).where(FeedbackRecord.content_id.in_(gc_ids_subq)))

    # 3. Chunks (FK → documents.id, no cascade)
    doc_ids_subq = select(Document.id).where(Document.conversation_id == conversation_id)
    await db.execute(sql_delete(Chunk).where(Chunk.document_id.in_(doc_ids_subq)))

    # 4. Direct FK references to this conversation
    await db.execute(sql_delete(ClassificationCorrection).where(ClassificationCorrection.conversation_id == conversation_id))
    await db.execute(sql_delete(AgentDecisionRecord).where(AgentDecisionRecord.conversation_id == conversation_id))
    await db.execute(sql_delete(TopicChangeLog).where(TopicChangeLog.conversation_id == conversation_id))

    # 5. Now safe to delete messages, generated_contents, documents, and the conversation
    await db.execute(sql_delete(Message).where(Message.conversation_id == conversation_id))
    await db.execute(sql_delete(GeneratedContent).where(GeneratedContent.conversation_id == conversation_id))
    await db.execute(sql_delete(Document).where(Document.conversation_id == conversation_id))
    await db.execute(sql_delete(Conversation).where(Conversation.id == conversation_id))
    await db.commit()


# ---------------------------------------------------------------------------
# Intelligent message routing (auto topic detection)
# ---------------------------------------------------------------------------

@router.post("/message", response_model=RoutedMessageResponse, status_code=status.HTTP_200_OK)
async def send_message(
    request: MessageRequest,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message with automatic topic detection.

    The backend:
    1. Runs the hybrid keyword+LLM analyzer to detect subject, topic, content_type.
    2. Compares the detected topic with the current conversation's topic.
    3. If the topic changed (or no conversation exists), a new conversation is created.
    4. Generates a response using the LLM pipeline.
    5. Returns routing info + generated content so the frontend can seamlessly
       switch to the new conversation when the topic changes.
    """
    user_id = get_current_user_id(authorization)

    routing = await ConversationService.process_message_and_route(
        user_id=user_id,
        user_prompt=request.user_prompt,
        db=db,
        conversation_id=request.conversation_id,
        document_id=request.document_id,
    )

    conversation_id = routing["conversation_id"]

    # Persist the user message with detected metadata
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="user",
        content=request.user_prompt,
        subject=routing.get("subject"),
        topic=routing.get("topic"),
        detected_content_type=routing.get("content_type"),
        detection_confidence=routing.get("confidence", 0.0),
        detection_method=routing.get("detection_method"),
        document_id=request.document_id,
    )
    db.add(user_msg)

    # Generate content via the RAG + agent pipeline
    bloom_tags = None
    try:
        generation_result = await ContentOrchestrator.generate_with_rag_and_agents(
            conversation_id=conversation_id,
            user_prompt=request.user_prompt,
            subject=routing.get("subject") or "General",
            topic=routing.get("topic") or "General",
            level=request.difficulty or "intermediate",
            user_id=user_id,
            document_id=request.document_id,
            db=db,
        )
        generated_content_text = generation_result.get("content", "")
        content_type = generation_result.get("content_type") or routing.get("content_type") or "text"
        bloom_tags = generation_result.get("bloom_tags")
    except Exception as exc:
        logger.error("Content generation failed for conversation %s: %s", conversation_id, exc)
        generated_content_text = ""
        content_type = routing.get("content_type") or "text"

    # Persist the assistant response
    assistant_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=generated_content_text,
        content_type=content_type,
        subject=routing.get("subject"),
        topic=routing.get("topic"),
        detected_content_type=content_type,
    )
    db.add(assistant_msg)

    # Update conversation metadata + timestamps
    subject = routing.get("subject")
    topic = routing.get("topic")
    # Safe fallback so `title` is always defined even if the DB lookup fails
    title = f"{subject or 'General'} - {topic or 'Untitled'}"

    try:
        conv_result = await db.execute(
            select(Conversation).filter(Conversation.id == conversation_id)
        )
        conversation = conv_result.scalar_one_or_none()

        # Only update title/subject/topic when we have real detected values.
        # Never overwrite an existing meaningful title with "General - Untitled".
        if conversation:
            now = datetime.utcnow()
            conversation.updated_at = now
            conversation.last_edited = now
            if subject and topic:
                title = f"{subject} - {topic}"
                conversation.title = title
                conversation.subject = subject
                conversation.primary_subject = subject
                conversation.topic = topic
                conversation.primary_topic = topic
            else:
                # Preserve whatever the conversation already has
                subject = conversation.primary_subject or conversation.subject
                topic = conversation.primary_topic or conversation.topic
                title = conversation.title or title

        await db.commit()
    except Exception as commit_err:
        logger.error("Error finalizing conversation %s: %s", conversation_id, commit_err)
        # Still return what we have; messages may not be saved but response is valid

    return RoutedMessageResponse(
        conversation_id=conversation_id,
        is_new_conversation=routing["is_new_conversation"],
        subject=subject,
        topic=topic,
        content_type=content_type,
        confidence=routing.get("confidence", 0.0),
        detection_method=routing.get("detection_method"),
        content=generated_content_text,
        title=title,
        bloom_tags=[BloomTag(**t) for t in bloom_tags] if bloom_tags else None,
    )


# ---------------------------------------------------------------------------
# Streaming message endpoint (SSE)
# ---------------------------------------------------------------------------

@router.post("/message/stream")
async def send_message_stream(
    request: MessageRequest,
    authorization: Optional[str] = Header(default=None),
):
    """
    SSE (Server-Sent Events) version of ``send_message``.

    Streams the generated content token-by-token while the conversation
    routing and analysis happen transparently.  The client receives:

        data: {"type": "meta",  "conversation_id": "...", "is_new": false, ...}
        data: {"type": "chunk", "content": "Hello "}
        data: {"type": "chunk", "content": "World"}
        data: {"type": "done",  "message_id": "...", "bloom_tags": [...]}

    Using ``text/event-stream`` with ``fetch + ReadableStream`` on the frontend.
    """
    user_id = get_current_user_id(authorization)

    async def event_stream() -> AsyncGenerator[dict, None]:
        async with async_session() as db:
            # ── 1. Route message ──────────────────────────────────────────────
            try:
                routing = await ConversationService.process_message_and_route(
                    user_id=user_id,
                    user_prompt=request.user_prompt,
                    db=db,
                    conversation_id=request.conversation_id,
                    document_id=request.document_id,
                )
            except Exception as exc:
                yield {"data": json.dumps({'type': 'error', 'message': str(exc)})}
                return

            conversation_id = routing["conversation_id"]
            subject = routing.get("subject") or "General"
            topic = routing.get("topic") or "General"

            # ── 2. Save user message ──────────────────────────────────────────
            user_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="user",
                content=request.user_prompt,
                subject=subject,
                topic=topic,
                detected_content_type=routing.get("content_type"),
                detection_confidence=routing.get("confidence", 0.0),
                detection_method=routing.get("detection_method"),
                document_id=request.document_id,
            )
            db.add(user_msg)
            await db.commit()

            # ── 3. Emit routing metadata immediately ──────────────────────────
            yield {"data": json.dumps({'type': 'meta', 'conversation_id': conversation_id, 'is_new_conversation': routing['is_new_conversation'], 'subject': subject, 'topic': topic})}

            # ── 4. Analyze (needed for stream context) ────────────────────────
            from app.agents.analyzer_agent import AnalyzerAgent
            from app.agents.reviewer_agent import ReviewerAgent as _Reviewer

            # Load document context if provided
            doc_context = None
            if request.document_id:
                try:
                    doc_res = await db.execute(
                        select(Message).filter()  # placeholder; load Document below
                    )
                    from app.models.models import Document as DocModel
                    doc_res2 = await db.execute(
                        select(DocModel).filter(DocModel.id == request.document_id)
                    )
                    doc_obj = doc_res2.scalar_one_or_none()
                    if doc_obj:
                        doc_context = doc_obj.original_content
                except Exception:
                    pass

            analysis = await AnalyzerAgent.analyze_with_context(
                user_prompt=request.user_prompt,
                subject=subject,
                topic=topic,
                document_context=doc_context,
                user_level=request.difficulty or "intermediate",
            )

            # ── 5. Stream generation ──────────────────────────────────────────
            from app.agents.generator_agent import GeneratorAgent as _Gen
            full_content = ""
            content_type = analysis["content_type"]

            try:
                async for chunk in _Gen.generate_stream(
                    content_type=content_type,
                    subject=subject,
                    topic=topic,
                    level=analysis["difficulty_level"],
                    user_prompt=request.user_prompt,
                    retrieved_context=analysis["retrieved_context"],
                    requirements=analysis["requirements"],
                ):
                    full_content += chunk
                    yield {"data": json.dumps({'type': 'chunk', 'content': chunk})}
            except Exception as exc:
                logger.error("Stream generation error: %s", exc)
                yield {"data": json.dumps({'type': 'error', 'message': 'Generation failed'})}
                return

            # ── 6. Save assistant message ─────────────────────────────────────
            bloom_tags = _Reviewer.tag_bloom_levels(full_content)

            assistant_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="assistant",
                content=full_content,
                content_type=content_type,
                subject=subject,
                topic=topic,
                detected_content_type=content_type,
            )
            db.add(assistant_msg)

            # Update conversation timestamps
            try:
                conv_res = await db.execute(
                    select(Conversation).filter(Conversation.id == conversation_id)
                )
                conv = conv_res.scalar_one_or_none()
                if conv:
                    now = datetime.utcnow()
                    conv.updated_at = now
                    conv.last_edited = now
                    if subject and topic:
                        conv.subject = subject
                        conv.topic = topic
                        conv.primary_subject = subject
                        conv.primary_topic = topic
                        conv.title = f"{subject} - {topic}"
            except Exception:
                pass

            await db.commit()
            await db.refresh(assistant_msg)

            # ── 7. Done event with final metadata ─────────────────────────────
            yield {"data": json.dumps({'type': 'done', 'message_id': assistant_msg.id, 'conversation_id': conversation_id, 'bloom_tags': bloom_tags, 'title': f'{subject} - {topic}'})}

    return EventSourceResponse(
        event_stream(),
        headers={"X-Accel-Buffering": "no"},
    )


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


# ---------------------------------------------------------------------------
# HITL: Message rating (thumbs up / thumbs down)
# ---------------------------------------------------------------------------

@router.post(
    "/{conversation_id}/messages/{message_id}/rate",
    response_model=MessageRateResponse,
)
async def rate_message(
    conversation_id: str,
    message_id: str,
    data: MessageRateRequest,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit 👍 (+1) or 👎 (-1) feedback on an assistant message.

    The rating is upserted — re-rating a message updates the existing record.
    Negative ratings with optional `feedback_text` are surfaced in future
    generation prompts so the model can avoid similar mistakes.
    """
    if data.rating not in (1, -1):
        raise HTTPException(status_code=422, detail="rating must be +1 or -1")

    user_id = get_current_user_id(authorization)

    # Verify conversation belongs to this user
    conv_result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Verify message exists in that conversation
    msg_result = await db.execute(
        select(Message).filter(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
        )
    )
    if not msg_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Message not found")

    # Upsert: one rating per (user, message)
    existing_result = await db.execute(
        select(MessageRating).filter(
            MessageRating.message_id == message_id,
            MessageRating.user_id == user_id,
        )
    )
    rating_record = existing_result.scalar_one_or_none()

    if rating_record:
        rating_record.rating = data.rating
        rating_record.feedback_text = data.feedback_text
        rating_record.timestamp = datetime.utcnow()
    else:
        rating_record = MessageRating(
            id=str(uuid.uuid4()),
            message_id=message_id,
            user_id=user_id,
            rating=data.rating,
            feedback_text=data.feedback_text,
        )
        db.add(rating_record)

    await db.commit()
    await db.refresh(rating_record)

    logger.info(
        "Message %s rated %+d by user %s%s",
        message_id, data.rating, user_id,
        f' — "{data.feedback_text[:60]}"' if data.feedback_text else "",
    )

    return MessageRateResponse(
        rating_id=rating_record.id,
        message_id=message_id,
        rating=rating_record.rating,
        recorded=True,
    )


# ---------------------------------------------------------------------------
# HITL: Classification correction (reclassify a misclassified conversation)
# ---------------------------------------------------------------------------

@router.patch(
    "/{conversation_id}/reclassify",
    response_model=ReclassifyResponse,
)
async def reclassify_conversation(
    conversation_id: str,
    data: ReclassifyRequest,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Correct the AI-inferred subject of a conversation.

    This does two things:
    1. Updates the conversation's subject / folder immediately.
    2. Saves a ClassificationCorrection record that is injected as a few-shot
       example the next time MetadataAnalyzer classifies a new message from
       this user — so the model progressively learns each user's terminology.
    """
    user_id = get_current_user_id(authorization)

    result = await db.execute(
        select(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .options(selectinload(Conversation.messages))
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    original_subject = conversation.primary_subject or conversation.subject

    # Auto-resolve folder from subject unless caller provides one explicitly
    folder_id = data.folder_id
    if folder_id is None:
        folder_id = await ConversationService._get_or_create_subject_folder(
            db=db, user_id=user_id, subject=data.subject
        )

    # Build a sample prompt snippet from the first user message (for few-shot use)
    sample_prompt: Optional[str] = None
    user_messages = [m for m in (conversation.messages or []) if m.role == "user"]
    if user_messages:
        first_user_msg = min(user_messages, key=lambda m: m.timestamp)
        sample_prompt = first_user_msg.content[:200]

    # Record the correction for future few-shot injection
    correction = ClassificationCorrection(
        id=str(uuid.uuid4()),
        user_id=user_id,
        conversation_id=conversation_id,
        original_subject=original_subject,
        corrected_subject=data.subject,
        sample_prompt=sample_prompt,
    )
    db.add(correction)

    # Update the conversation
    conversation.subject = data.subject
    conversation.primary_subject = data.subject
    topic = conversation.primary_topic or conversation.topic or "Untitled"
    new_title = f"{data.subject} - {topic}"
    conversation.title = new_title
    conversation.folder_id = folder_id
    conversation.updated_at = datetime.utcnow()

    await db.commit()

    logger.info(
        "Conversation %s reclassified: '%s' → '%s' (folder=%s)",
        conversation_id, original_subject, data.subject, folder_id,
    )

    return ReclassifyResponse(
        conversation_id=conversation_id,
        old_subject=original_subject,
        new_subject=data.subject,
        folder_id=folder_id,
        title=new_title,
    )


# ---------------------------------------------------------------------------
# HITL: Professor edits the AI output → LLM refines using original vs edited
# ---------------------------------------------------------------------------

@router.post(
    "/{conversation_id}/messages/{message_id}/refine",
    response_model=RefineResponse,
)
async def refine_message(
    conversation_id: str,
    message_id: str,
    data: RefineRequest,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    HITL edit-and-refine loop.

    The professor edits the AI's raw output (e.g. an exam or guide) directly in
    the chat, then submits it back.  The backend passes BOTH the original and the
    edited version to the LLM and asks it to produce a polished final version that:

      1. Preserves ALL intentional changes the professor made.
      2. Fills in any gaps or rough edits the professor left partial.
      3. Maintains consistent academic formatting throughout.

    The refined response is saved as a new assistant message in the same
    conversation (no topic re-routing — the conversation continues normally).
    """
    from app.services.llm_service import LLMService

    user_id = get_current_user_id(authorization)

    # Verify conversation ownership
    conv_result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Fetch the original assistant message
    msg_result = await db.execute(
        select(Message).filter(
            Message.id == message_id,
            Message.conversation_id == conversation_id,
            Message.role == "assistant",
        )
    )
    original_message = msg_result.scalar_one_or_none()
    if not original_message:
        raise HTTPException(status_code=404, detail="Message not found or not an assistant message")

    original_content = original_message.content
    edited_content = data.edited_content.strip()

    if not edited_content:
        raise HTTPException(status_code=422, detail="edited_content cannot be empty")

    # Build the comparison / refinement prompt
    refine_prompt = f"""You are refining academic content based on a professor's direct edits.

ORIGINAL AI-generated content:
---
{original_content}
---

PROFESSOR'S EDITED VERSION:
---
{edited_content}
---

The professor made specific intentional changes. Your task is to produce a FINAL polished version that:
1. Preserves ALL changes the professor made — they are deliberate corrections
2. Fills in any rough or incomplete edits, completing them with the same intent
3. Keeps consistent academic formatting, numbering, and style throughout
4. Does NOT revert any of the professor's modifications
5. Does NOT add new content beyond what is implied by the professor's edits

Return ONLY the final refined content with no preamble, explanation, or markdown fence."""

    try:
        refined_content = await LLMService.generate_with_prompt(refine_prompt)
    except Exception as exc:
        logger.error("Refinement LLM call failed for message %s: %s", message_id, exc)
        raise HTTPException(status_code=500, detail="Refinement generation failed")

    # Save the refined output as a new assistant message in the same conversation
    # (bypasses topic routing — this is a direct continuation, not a new topic)
    refined_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role="assistant",
        content=refined_content,
        content_type=original_message.content_type,
        subject=original_message.subject,
        topic=original_message.topic,
        detected_content_type=original_message.detected_content_type,
        detection_confidence=original_message.detection_confidence or 0.0,
        detection_method=original_message.detection_method,
    )
    db.add(refined_message)

    # Update conversation timestamp (editing IS activity)
    conversation.updated_at = datetime.utcnow()
    conversation.last_edited = datetime.utcnow()

    await db.commit()
    await db.refresh(refined_message)

    logger.info(
        "Refined message %s → new message %s in conversation %s",
        message_id, refined_message.id, conversation_id,
    )

    return RefineResponse(
        message_id=refined_message.id,
        conversation_id=conversation_id,
        content=refined_content,
        content_type=refined_message.content_type,
        timestamp=refined_message.timestamp.isoformat(),
    )
