"""
Content Service - High-level content generation and management
"""
import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import GeneratedContent, FeedbackRecord
from app.orchestration.content_orchestrator import ContentOrchestrator
from app.agents.feedback_agent import FeedbackAgent

logger = logging.getLogger(__name__)


class ContentService:
    """Service for content generation, feedback, and retrieval"""

    @staticmethod
    async def generate_content(
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        user_prompt: str,
        subject: str,
        topic: str,
        level: str,
        content_type: Optional[str] = None,
        document_context: Optional[str] = None,
        previous_feedback: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate academic content using the RAG + Agent pipeline.

        Returns a dict with the generated content and metadata.
        """
        result = await ContentOrchestrator.generate_with_rag_and_agents(
            conversation_id=conversation_id,
            user_prompt=user_prompt,
            subject=subject,
            topic=topic,
            level=level,
            user_id=user_id,
            document_context=document_context,
            previous_feedback=previous_feedback,
            db=db,
        )
        logger.info(
            f"Generated {result.get('content_type')} content for conversation {conversation_id}"
        )
        return result

    @staticmethod
    async def get_content(
        db: AsyncSession,
        content_id: str,
    ) -> Optional[GeneratedContent]:
        """Get generated content by ID"""
        result = await db.execute(
            select(GeneratedContent).filter(GeneratedContent.id == content_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_conversation_content(
        db: AsyncSession,
        conversation_id: str,
    ) -> List[GeneratedContent]:
        """Get all generated content for a conversation"""
        result = await db.execute(
            select(GeneratedContent)
            .filter(GeneratedContent.conversation_id == conversation_id)
            .order_by(GeneratedContent.created_at)
        )
        return result.scalars().all()

    @staticmethod
    async def submit_feedback(
        db: AsyncSession,
        content_id: str,
        feedback_text: str,
        status: str,
        editor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit teacher feedback on generated content.

        Args:
            content_id: ID of the generated content
            feedback_text: Teacher's feedback text
            status: "approved", "needs_revision", or "rejected"
            editor_name: Name of the teacher submitting feedback

        Returns:
            Feedback processing result
        """
        feedback_result = await FeedbackAgent.process_feedback(
            content_id=content_id,
            feedback_text=feedback_text,
            status=status,
            editor_name=editor_name or "Anonymous",
            db=db,
        )
        await db.commit()
        logger.info(f"Feedback submitted for content {content_id}: {status}")
        return feedback_result

    @staticmethod
    async def get_feedback_examples(
        db: AsyncSession,
        user_id: str,
        content_type: str,
        subject: str,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get approved content examples for few-shot learning"""
        return await FeedbackAgent.get_learning_examples(
            user_id=user_id,
            content_type=content_type,
            subject=subject,
            db=db,
            limit=limit,
        )
