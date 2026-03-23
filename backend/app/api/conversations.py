from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import uuid
from datetime import datetime
from app.core.database import get_db
from app.core.security import decode_token
from app.schemas import (
    ConversationCreate, ConversationResponse, 
    MessageCreate, MessageResponse,
    GeneratedContentResponse, GenerationRequest, GenerationResponse,
    FeedbackSubmit, RegenerationRequest
)
from app.models.models import (
    Conversation, Message, GeneratedContent, FeedbackRecord, User
)
from app.orchestration.content_orchestrator import ContentOrchestrator
from app.agents.feedback_agent import FeedbackAgent
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_current_user_id(token: str) -> str:
    """Extract user ID from token"""
    if not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    token_str = token.replace("Bearer ", "")
    payload = decode_token(token_str)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return payload.get("sub")


@router.get("", response_model=list[ConversationResponse])
async def get_conversations(
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all conversations for user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    result = await db.execute(
        select(Conversation)
        .filter(Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
        .options(selectinload(Conversation.generated_contents))
    )
    conversations = result.scalars().all()
    return conversations


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get specific conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    result = await db.execute(
        select(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        .options(selectinload(Conversation.messages))
        .options(selectinload(Conversation.generated_contents))
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Create new conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
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
    data: ConversationCreate,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Update conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation.title = data.title
    conversation.subject = data.subject
    conversation.topic = data.topic
    conversation.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Delete conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    await db.delete(conversation)
    await db.commit()
    
    return {"detail": "Conversation deleted"}


@router.post("/{conversation_id}/generate-with-rag", response_model=GenerationResponse)
async def generate_with_rag_pipeline(
    conversation_id: str,
    request: GenerationRequest,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate content using the RAG + Agent pipeline
    
    This endpoint uses:
    1. Analyzer Agent: Analyzes prompt and retrieves context
    2. Generator Agent: Generates content with RAG context
    3. Reviewer Agent: Validates and re-ranks content
    4. Human-in-the-Loop: Ready for feedback
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization")
        
        user_id = get_current_user_id(authorization)
        
        # Verify conversation exists
        result = await db.execute(
            select(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get any uploaded documents for context
        document_context = ""
        if request.include_document and request.document_id:
            # In production, would retrieve document content from DB
            pass
        
        # Get previous feedback if this is a regeneration
        previous_feedback = None
        if conversation.generated_contents:
            # Get feedback history
            previous_feedback = []
            for content in conversation.generated_contents:
                for feedback in content.feedback_records:
                    previous_feedback.append({
                        "feedback": feedback.feedback,
                        "status": feedback.status
                    })
        
        # Run orchestrator pipeline
        generation_result = await ContentOrchestrator.generate_with_rag_and_agents(
            conversation_id=conversation_id,
            user_prompt=request.user_prompt,
            subject=request.subject,
            topic=request.topic,
            level=request.level,
            user_id=user_id,
            document_context=document_context,
            previous_feedback=previous_feedback,
            db=db,
        )
        
        # Save generated content
        content = GeneratedContent(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            content_type=generation_result["content_type"],
            title=f"{generation_result['content_type'].title()} - {request.topic}",
            content=generation_result["content"],
            version=generation_result["version"],
        )
        
        db.add(content)
        conversation.updated_at = datetime.utcnow()
        conversation.last_edited = datetime.utcnow()
        
        await db.commit()
        await db.refresh(content)
        
        logger.info(f"Content generated: {content.id} (version {generation_result['version']})")
        
        return GenerationResponse(
            conversation_id=conversation_id,
            content=generation_result["content"],
            content_type=generation_result["content_type"],
            title=content.title,
            version=generation_result["version"],
            status=generation_result["status"],
            review_score=generation_result["review_score"],
            generation_attempts=generation_result["generation_attempts"],
            analysis=generation_result.get("analysis"),
            review=generation_result.get("review"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: str,
    data: MessageCreate,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Add message to conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    # Verify conversation exists
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=data.role,
        content=data.content,
        content_type=data.content_type,
    )
    
    db.add(message)
    await db.commit()
    await db.refresh(message)
    
    return message


@router.post("/{conversation_id}/content/{content_id}/feedback")
async def submit_feedback(
    conversation_id: str,
    content_id: str,
    feedback_data: FeedbackSubmit,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit feedback for generated content (Human-in-the-Loop)
    
    Status options:
    - "approved": Content is good
    - "needs_revision": Request regeneration with feedback
    - "rejected": Completely reject
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization")
        
        user_id = get_current_user_id(authorization)
        
        # Verify conversation and content exist
        result = await db.execute(
            select(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        result = await db.execute(
            select(GeneratedContent).filter(
                GeneratedContent.id == content_id,
                GeneratedContent.conversation_id == conversation_id
            )
        )
        content = result.scalar_one_or_none()
        
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Process feedback
        feedback_result = await ContentOrchestrator.process_teacher_feedback(
            content_id=content_id,
            feedback_text=feedback_data.feedback,
            status=feedback_data.status,
            editor_name=feedback_data.editor_name or user_id,
            db=db,
        )
        
        # Save feedback record
        feedback_record = FeedbackRecord(
            id=str(uuid.uuid4()),
            content_id=content_id,
            feedback=feedback_data.feedback,
            status=feedback_data.status,
            editor_name=feedback_data.editor_name or "Teacher",
        )
        
        db.add(feedback_record)
        await db.commit()
        
        logger.info(f"Feedback recorded: {content_id} - {feedback_data.status}")
        
        result = {
            "feedback_id": feedback_record.id,
            "status": feedback_data.status,
            "next_action": feedback_result["next_action"],
            "regeneration_requested": feedback_result["regeneration_requested"],
        }
        
        if feedback_data.request_regeneration:
            result["regeneration_instructions"] = await FeedbackAgent.get_regeneration_instructions(
                feedback_text=feedback_data.feedback,
                content=content.content,
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/regenerate", response_model=GenerationResponse)
async def regenerate_with_feedback(
    conversation_id: str,
    request: RegenerationRequest,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate content based on feedback (Human-in-the-Loop cycle)
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization")
        
        user_id = get_current_user_id(authorization)
        
        # Verify conversation exists
        result = await db.execute(
            select(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get previous content
        result = await db.execute(
            select(GeneratedContent).filter(
                GeneratedContent.id == request.content_id,
                GeneratedContent.conversation_id == conversation_id
            )
        )
        prev_content = result.scalar_one_or_none()
        
        if not prev_content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Get feedback history
        previous_feedback = await FeedbackAgent.update_feedback_history(
            content_id=request.content_id,
            new_feedback=request.feedback_text,
            db=db,
        )
        
        # Regenerate with feedback context
        generation_result = await ContentOrchestrator.generate_with_rag_and_agents(
            conversation_id=conversation_id,
            user_prompt=prev_content.content[:500] + f"\n\nFeedback: {request.feedback_text}",
            subject=conversation.subject or "General",
            topic=conversation.topic or "General",
            level="intermediate",
            user_id=user_id,
            document_context=request.feedback_text,
            previous_feedback=previous_feedback,
            db=db,
        )
        
        # Save new version
        new_content = GeneratedContent(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            content_type=prev_content.content_type,
            title=prev_content.title + f" (v{prev_content.version + 1})",
            content=generation_result["content"],
            version=prev_content.version + 1,
        )
        
        db.add(new_content)
        conversation.updated_at = datetime.utcnow()
        conversation.last_edited = datetime.utcnow()
        
        await db.commit()
        await db.refresh(new_content)
        
        logger.info(f"Content regenerated: {new_content.id} (version {new_content.version})")
        
        return GenerationResponse(
            conversation_id=conversation_id,
            content=new_content.content,
            content_type=new_content.content_type,
            title=new_content.title,
            version=new_content.version,
            status="regenerated",
            review_score=generation_result["review_score"],
            generation_attempts=generation_result["generation_attempts"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[ConversationResponse])
async def get_conversations(
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all conversations for user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    result = await db.execute(
        select(Conversation)
        .filter(Conversation.user_id == user_id)
        .options(selectinload(Conversation.messages))
        .options(selectinload(Conversation.generated_contents))
    )
    conversations = result.scalars().all()
    return conversations


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get specific conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    result = await db.execute(
        select(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        .options(selectinload(Conversation.messages))
        .options(selectinload(Conversation.generated_contents))
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Create new conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
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
    data: dict,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Update conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    for key, value in data.items():
        if hasattr(conversation, key):
            setattr(conversation, key, value)
    
    conversation.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Delete conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    await db.delete(conversation)
    await db.commit()
    
    return {"detail": "Conversation deleted"}


@router.post("/{conversation_id}/generate")
async def generate_content(
    conversation_id: str,
    request: LLMRequest,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Generate content for conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    # Verify conversation exists and belongs to user
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    try:
        # Generate content using LLM
        generated_text = await LLMService.generate_content(
            content_type=request.content_type,
            subject=request.subject,
            topic=request.topic,
            level=request.level,
            additional_context=request.additional_context,
            previous_feedback=request.previous_feedback,
        )
        
        # Save generated content to database
        content = GeneratedContent(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            content_type=request.content_type,
            title=f"{request.content_type.title()} on {request.topic}",
            content=generated_text,
            version=1,
        )
        db.add(content)
        
        # Add to vector database
        await VectorDatabaseService.add_documents(
            documents=[generated_text],
            metadatas=[{
                "content_id": content.id,
                "conversation_id": conversation_id,
                "subject": request.subject,
                "topic": request.topic,
            }],
            ids=[content.id],
        )
        
        await db.commit()
        await db.refresh(content)
        
        return {
            "generatedContent": generated_text,
            "contentType": request.content_type,
            "suggestedTitle": content.title,
            "confidence": 0.95,  # Placeholder
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    message: MessageCreate,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Add message to conversation"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    # Verify conversation exists
    result = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
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


@router.post("/content/{content_id}/feedback")
async def submit_feedback(
    content_id: str,
    feedback_data: FeedbackSubmit,
    authorization: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Submit feedback on generated content"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    user_id = get_current_user_id(authorization)
    
    # Get content and verify user is the owner
    result = await db.execute(
        select(GeneratedContent)
        .filter(GeneratedContent.id == content_id)
        .join(Conversation)
        .filter(Conversation.user_id == user_id)
    )
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Create feedback record
    feedback = FeedbackRecord(
        id=str(uuid.uuid4()),
        content_id=content_id,
        feedback=feedback_data.feedback,
        status=feedback_data.status,
        editor_name="Professor",  # Could be extracted from user
    )
    
    db.add(feedback)
    content.feedback = feedback_data.feedback
    content.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"detail": "Feedback submitted", "feedback_id": feedback.id}
