"""
Conversation Service - CRUD operations for conversations and messages
"""
import uuid
import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.models import Conversation, Message, GeneratedContent

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
    ) -> Message:
        """Add a message to a conversation"""
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            content_type=content_type,
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
