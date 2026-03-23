"""
Conversation Service - CRUD operations for conversations and messages
"""
import json
import uuid
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.models import Conversation, Document, Message, GeneratedContent

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing conversations and their messages"""

    @staticmethod
    async def get_conversations_by_user(
        db: AsyncSession,
        user_id: str,
    ) -> List[Conversation]:
        """Get all conversations for a user"""
        result = await db.execute(
            select(Conversation)
            .filter(Conversation.user_id == user_id)
            .options(
                selectinload(Conversation.messages),
                selectinload(Conversation.generated_contents),
            )
        )
        return result.scalars().all()

    @staticmethod
    async def get_conversation(
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
    ) -> Optional[Conversation]:
        """Get a conversation by ID, ensuring it belongs to the user"""
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
        return result.scalar_one_or_none()

    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        user_id: str,
        title: str,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            subject=subject,
            topic=topic,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        logger.info(f"Created conversation {conversation.id} for user {user_id}")
        return conversation

    @staticmethod
    async def update_conversation(
        db: AsyncSession,
        conversation: Conversation,
        title: Optional[str] = None,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Conversation:
        """Update conversation fields"""
        if title is not None:
            conversation.title = title
        if subject is not None:
            conversation.subject = subject
        if topic is not None:
            conversation.topic = topic
        conversation.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        conversation: Conversation,
    ) -> None:
        """Delete a conversation and all related data"""
        await db.delete(conversation)
        await db.commit()
        logger.info(f"Deleted conversation {conversation.id}")

    @staticmethod
    async def add_message(
        db: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        content_type: Optional[str] = None,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        detected_content_type: Optional[str] = None,
        detection_confidence: float = 0.0,
        detection_method: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> Message:
        """Add a message to a conversation"""
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            content_type=content_type,
            subject=subject,
            topic=topic,
            detected_content_type=detected_content_type,
            detection_confidence=detection_confidence,
            detection_method=detection_method,
            document_id=document_id,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        conversation_id: str,
    ) -> List[Message]:
        """Get all messages for a conversation ordered by timestamp"""
        result = await db.execute(
            select(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
        )
        return result.scalars().all()

    @staticmethod
    async def save_generated_content(
        db: AsyncSession,
        conversation_id: str,
        content_type: str,
        title: str,
        content: str,
        version: int = 1,
    ) -> GeneratedContent:
        """Save generated content to the database"""
        generated = GeneratedContent(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            content_type=content_type,
            title=title,
            content=content,
            version=version,
        )
        db.add(generated)
        await db.commit()
        await db.refresh(generated)
        logger.info(f"Saved generated content {generated.id} (v{version})")
        return generated

    # ---------------------------------------------------------------------------
    # Intelligent topic routing
    # ---------------------------------------------------------------------------

    @staticmethod
    async def process_message_and_route(
        user_id: str,
        user_prompt: str,
        db: AsyncSession,
        conversation_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect topic from prompt + optional document, compare with the current
        conversation topic, and create a new conversation if the topic changed.

        Returns:
            {
                "conversation_id": str,
                "is_new_conversation": bool,
                "subject": str | None,
                "topic": str | None,
                "content_type": str | None,
                "confidence": float,
                "detection_method": str | None,
            }
        """
        from app.agents.metadata_analyzer import MetadataAnalyzer

        # 1. Collect document metadata if a document_id was supplied
        doc_metadata: Optional[Dict[str, Any]] = None
        if document_id:
            doc_metadata = await ConversationService._get_document_metadata(
                document_id, db
            )

        # 2. Detect metadata from the user prompt (merged with document metadata)
        detected = MetadataAnalyzer.hybrid_detect(user_prompt, document_metadata=doc_metadata)

        # 3. Check whether the topic changed relative to the current conversation
        current_conversation: Optional[Conversation] = None
        topic_changed = False

        if conversation_id:
            result = await db.execute(
                select(Conversation).filter(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            current_conversation = result.scalar_one_or_none()

            if current_conversation:
                current_topic = current_conversation.primary_topic or current_conversation.topic
                new_topic = detected.get("topic")

                if current_topic and new_topic and current_topic.lower() != new_topic.lower():
                    topic_changed = True
                    logger.info(
                        "Topic changed from '%s' to '%s' – creating new conversation",
                        current_topic,
                        new_topic,
                    )

        # 4. Create a new conversation when the topic changed or there is no existing one
        is_new = topic_changed or current_conversation is None
        if is_new:
            subject = detected.get("subject") or "General"
            topic = detected.get("topic") or "Untitled"
            title = f"{subject} - {topic}"

            new_conversation = Conversation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=title,
                subject=subject,
                topic=topic,
                primary_subject=subject,
                primary_topic=topic,
            )
            db.add(new_conversation)
            await db.commit()
            await db.refresh(new_conversation)
            conversation_id = new_conversation.id

        return {
            "conversation_id": conversation_id,
            "is_new_conversation": is_new,
            "subject": detected.get("subject"),
            "topic": detected.get("topic"),
            "content_type": detected.get("content_type"),
            "confidence": detected.get("confidence", 0.0),
            "detection_method": detected.get("method"),
        }

    @staticmethod
    async def _get_document_metadata(document_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Detect subject/topic from an uploaded document's stored content."""
        from app.agents.metadata_analyzer import MetadataAnalyzer

        result = await db.execute(
            select(Document).filter(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            return {}

        detected = MetadataAnalyzer.hybrid_detect(document.original_content)
        return {
            "subject": detected.get("subject"),
            "topic": detected.get("topic"),
        }
