"""
Feedback Learning Service - Manages few-shot prompting with teacher feedback
Persists feedback examples and builds prompts that incorporate past corrections.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import FeedbackRecord, GeneratedContent

logger = logging.getLogger(__name__)


class FeedbackLearningService:
    """
    Retrieves teacher feedback from the database and converts it into
    few-shot examples that guide future content generation.
    """

    @staticmethod
    async def get_few_shot_examples(
        db: AsyncSession,
        user_id: str,
        content_type: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent approved feedback records and format them as few-shot
        examples for LLM prompting.

        Args:
            db: Database session.
            user_id: Teacher's user ID (used to scope results to their conversations).
            content_type: Optional filter by content type (exam, guide, etc.).
            subject: Optional filter by academic subject.
            limit: Maximum number of examples to return.

        Returns:
            List of dicts with keys: content_type, content_snippet, feedback, status.
        """
        try:
            # Join through conversations to scope by user
            from app.models.models import Conversation
            stmt = (
                select(FeedbackRecord, GeneratedContent)
                .join(GeneratedContent, FeedbackRecord.content_id == GeneratedContent.id)
                .join(Conversation, GeneratedContent.conversation_id == Conversation.id)
                .filter(Conversation.user_id == user_id)
                .order_by(FeedbackRecord.timestamp.desc())
                .limit(limit * 3)  # Fetch extra to allow filtering
            )
            if content_type:
                stmt = stmt.filter(GeneratedContent.content_type == content_type)
            if subject:
                stmt = stmt.filter(Conversation.subject == subject)

            result = await db.execute(stmt)
            rows = result.all()

            examples: List[Dict[str, Any]] = []
            for feedback_record, generated_content in rows:
                if len(examples) >= limit:
                    break
                snippet = (generated_content.content or "")[:400]
                examples.append({
                    "content_type": generated_content.content_type,
                    "content_snippet": snippet,
                    "feedback": feedback_record.feedback,
                    "status": feedback_record.status,
                })

            logger.info(
                f"Retrieved {len(examples)} few-shot examples for user {user_id}"
            )
            return examples

        except Exception as exc:
            logger.error(f"Error fetching few-shot examples: {exc}")
            return []

    @staticmethod
    def build_few_shot_prompt_section(examples: List[Dict[str, Any]]) -> str:
        """
        Convert few-shot examples into a formatted prompt section.

        Args:
            examples: Output of :meth:`get_few_shot_examples`.

        Returns:
            Formatted string to prepend to a generation prompt.
        """
        if not examples:
            return ""

        lines = [
            "### Teacher Feedback Examples (use these to improve your output):\n"
        ]
        for idx, ex in enumerate(examples, start=1):
            lines.append(f"Example {idx} [{ex.get('content_type', 'content')}]:")
            lines.append(f"  Content snippet: {ex.get('content_snippet', '')[:200]}...")
            lines.append(f"  Teacher feedback: {ex.get('feedback', '')}")
            lines.append(f"  Outcome: {ex.get('status', 'unknown')}\n")

        return "\n".join(lines)

    @staticmethod
    async def record_feedback(
        db: AsyncSession,
        content_id: str,
        feedback_text: str,
        status: str,
        editor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persist a teacher feedback record for future few-shot use and auditing.

        Args:
            db: Database session.
            content_id: ID of the generated content being reviewed.
            feedback_text: Teacher's textual feedback.
            status: One of "approved", "needs_revision", "rejected".
            editor_name: Name of the teacher (optional).

        Returns:
            Dict with the new feedback record ID and next action.
        """
        try:
            from app.models.models import FeedbackRecord
            from datetime import datetime

            record = FeedbackRecord(
                content_id=content_id,
                feedback=feedback_text,
                status=status,
                editor_name=editor_name,
            )
            db.add(record)

            # Also update the parent content's feedback summary field
            content_result = await db.execute(
                select(GeneratedContent).filter(GeneratedContent.id == content_id)
            )
            content = content_result.scalar_one_or_none()
            if content:
                content.feedback = feedback_text
                content.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(record)

            next_action = {
                "approved": "no_action",
                "needs_revision": "regenerate",
                "rejected": "regenerate",
            }.get(status, "no_action")

            logger.info(
                f"Recorded feedback {record.id} for content {content_id}: {status}"
            )
            return {
                "feedback_id": record.id,
                "status": status,
                "next_action": next_action,
            }

        except Exception as exc:
            logger.error(f"Error recording feedback: {exc}")
            raise
