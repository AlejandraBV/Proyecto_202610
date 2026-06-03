"""Service for detecting topic changes and managing automatic chat creation"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Conversation, TopicChangeLog, Message, Folder
from typing import Optional, Tuple
import json


class TopicDetectionService:
    """Detects topic changes and automatically creates new chats when user switches themes"""
    
    # Common keywords for each subject to detect topic changes
    SUBJECT_KEYWORDS = {
        "Biology": ["cell", "organism", "ecosystem", "dna", "protein", "photosynthesis", "reproduction", "mutation", "gene", "evolution"],
        "Chemistry": ["atom", "molecule", "reaction", "acid", "base", "bond", "electron", "periodic", "oxidation", "compound"],
        "Physics": ["force", "energy", "momentum", "wave", "particle", "gravity", "quantum", "motion", "acceleration", "field"],
        "Mathematics": ["equation", "function", "integral", "derivative", "matrix", "vector", "theorem", "proof", "algebra", "geometry"],
        "History": ["war", "revolution", "civilization", "empire", "dynasty", "colonial", "independence", "period", "era", "century"],
        "Literature": ["character", "plot", "theme", "metaphor", "narrative", "protagonist", "dialogue", "setting", "conflict", "author"],
        "Geography": ["continent", "country", "climate", "terrain", "border", "population", "region", "latitude", "natural", "resource"],
        "Economics": ["market", "supply", "demand", "inflation", "trade", "production", "consumer", "commodity", "price", "currency"],
    }
    
    @staticmethod
    async def detect_topic_change(
        db: AsyncSession,
        conversation_id: str,
        current_message_topic: str,
        current_message_subject: str,
        detection_confidence: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect if user has switched to a different topic
        
        Returns:
            Tuple of (has_changed, new_conversation_id)
            - has_changed: True if a topic change was detected
            - new_conversation_id: ID of new conversation if created, None otherwise
        """
        # Get the current conversation
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalars().first()
        
        if not conversation:
            return False, None
        
        # Get locked topic (the topic this conversation is focused on)
        locked_topic = conversation.locked_topic or conversation.primary_topic
        
        # If no locked topic yet, lock the current one
        if not locked_topic:
            conversation.locked_topic = current_message_topic
            conversation.primary_topic = current_message_topic
            conversation.primary_subject = current_message_subject
            await db.commit()
            return False, None
        
        # Check if topic has changed significantly
        topic_changed = (
            current_message_topic and
            locked_topic and
            current_message_topic.lower() != locked_topic.lower() and
            detection_confidence > 0.7  # Only if we're confident about the change
        )
        
        if not topic_changed:
            return False, None
        
        # Topic has changed - log the change and create new chat
        change_log = TopicChangeLog(
            conversation_id=conversation_id,
            old_topic=locked_topic,
            new_topic=current_message_topic,
            detection_confidence=detection_confidence
        )
        db.add(change_log)
        
        # Create new conversation with the new topic
        new_conversation = Conversation(
            user_id=conversation.user_id,
            folder_id=conversation.folder_id,  # Keep same folder
            title=f"{current_message_subject}: {current_message_topic}",
            subject=current_message_subject,
            topic=current_message_topic,
            primary_subject=current_message_subject,
            primary_topic=current_message_topic,
            locked_topic=current_message_topic,
        )
        db.add(new_conversation)
        await db.flush()  # Flush to get the new conversation ID
        
        # Update the change log with new chat ID
        change_log.new_chat_id = new_conversation.id
        change_log.automatic_new_chat_created = True
        
        await db.commit()
        
        return True, new_conversation.id
    
    @staticmethod
    async def set_locked_topic(
        db: AsyncSession,
        conversation_id: str,
        topic: str,
        subject: Optional[str] = None
    ):
        """Explicitly lock a topic for a conversation"""
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalars().first()
        
        if conversation:
            conversation.locked_topic = topic
            if subject:
                conversation.primary_subject = subject
            conversation.primary_topic = topic
            await db.commit()
    
    @staticmethod
    async def get_or_create_folder_for_topic(
        db: AsyncSession,
        user_id: str,
        topic: str,
        subject: Optional[str] = None
    ) -> str:
        """Get or create a folder for organizing conversations by topic"""
        # Try to find existing folder with this topic as name
        folder_name = f"{subject}: {topic}" if subject else topic
        
        result = await db.execute(
            select(Folder).where(
                (Folder.user_id == user_id) &
                (Folder.name == folder_name)
            )
        )
        folder = result.scalars().first()
        
        if folder:
            return folder.id
        
        # Create new folder
        new_folder = Folder(
            user_id=user_id,
            name=folder_name,
            description=f"Conversations about {topic}" + (f" in {subject}" if subject else ""),
            color=TopicDetectionService._get_color_for_subject(subject),
            icon="folder",
        )
        db.add(new_folder)
        await db.flush()
        return new_folder.id
    
    @staticmethod
    def _get_color_for_subject(subject: Optional[str]) -> str:
        """Get a color for the folder based on subject"""
        color_map = {
            "Biology": "#10B981",  # Green
            "Chemistry": "#F59E0B",  # Amber
            "Physics": "#3B82F6",  # Blue
            "Mathematics": "#EF4444",  # Red
            "History": "#8B5CF6",  # Purple
            "Literature": "#EC4899",  # Pink
            "Geography": "#06B6D4",  # Cyan
            "Economics": "#6366F1",  # Indigo
        }
        return color_map.get(subject, "#3B82F6")
    
    @staticmethod
    async def get_all_topics_in_conversation(
        db: AsyncSession,
        conversation_id: str
    ) -> list:
        """Get all topics discussed in a conversation"""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
        )
        messages = result.scalars().all()
        
        topics = set()
        for msg in messages:
            if msg.topic:
                topics.add(msg.topic)
        
        return list(topics)
    
    @staticmethod
    async def mark_topic_change_trigger(
        db: AsyncSession,
        message_id: str
    ):
        """Mark a message as the trigger for a new chat (topic change)"""
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalars().first()
        
        if message:
            message.triggered_new_chat = True
            await db.commit()
