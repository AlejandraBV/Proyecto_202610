"""
Feedback Agent - Processes teacher feedback and updates few-shot examples
Implements human-in-the-loop learning
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import FeedbackRecord, GeneratedContent
import json

logger = logging.getLogger(__name__)


class FeedbackAgent:
    """Processes feedback from teachers and updates learning examples"""
    
    @staticmethod
    async def process_feedback(
        content_id: str,
        feedback_text: str,
        status: str,  # "approved", "needs_revision", "rejected"
        editor_name: str,
        db: AsyncSession = None,
    ) -> Dict[str, Any]:
        """
        Process teacher feedback
        
        Args:
            content_id: Generated content ID
            feedback_text: Teacher's feedback
            status: Approval status
            editor_name: Name of teacher
            db: Database session
        
        Returns:
            Feedback processing result
        """
        try:
            # Save feedback to database
            feedback_record = FeedbackRecord(
                content_id=content_id,
                feedback=feedback_text,
                status=status,
                editor_name=editor_name,
            )
            
            if db:
                db.add(feedback_record)
                await db.flush()
            
            # Determine next action
            next_action = FeedbackAgent._determine_action(status)
            
            result = {
                "feedback_id": feedback_record.id,
                "status": status,
                "next_action": next_action,
                "learning_recorded": status == "approved",
                "regeneration_requested": status == "needs_revision",
            }
            
            logger.info(f"Feedback processed: {status} (action: {next_action})")
            return result
            
        except Exception as e:
            logger.error(f"Error in feedback agent: {e}")
            raise
    
    @staticmethod
    def _determine_action(status: str) -> str:
        """Determine what action to take based on feedback status"""
        if status == "approved":
            return "store_as_example"
        elif status == "needs_revision":
            return "request_regeneration_with_feedback"
        elif status == "rejected":
            return "request_regeneration_completely_new"
        else:
            return "none"
    
    @staticmethod
    async def get_learning_examples(
        user_id: str,
        content_type: str,
        subject: str,
        db: AsyncSession,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get approved examples for few-shot learning
        
        Args:
            user_id: Teacher's user ID
            content_type: Type of content to get examples for
            subject: Academic subject
            db: Database session
            limit: Number of examples to return
        
        Returns:
            List of approved examples for few-shot prompting
        """
        try:
            # Query for approved content of this user
            query = select(GeneratedContent, FeedbackRecord).join(
                FeedbackRecord,
                GeneratedContent.id == FeedbackRecord.content_id
            ).join(
                'conversation'
            ).where(
                FeedbackRecord.status == "approved",
                GeneratedContent.content_type == content_type,
            )
            
            result = await db.execute(query)
            records = result.fetchall()
            
            # Extract content and format for few-shot learning
            examples = []
            for content, feedback in records[:limit]:
                examples.append({
                    "content": content.content,
                    "title": content.title,
                    "feedback": feedback.feedback,
                    "type": content_type,
                })
            
            logger.info(f"Retrieved {len(examples)} learning examples for {content_type}")
            return examples
            
        except Exception as e:
            logger.warning(f"Could not retrieve learning examples: {e}")
            return []
    
    @staticmethod
    async def get_regeneration_instructions(
        feedback_text: str,
        content: str,
        previous_feedback: str = None,
    ) -> str:
        """
        Generate instructions for regeneration based on feedback
        
        Args:
            feedback_text: Teacher's feedback
            content: Original generated content
            previous_feedback: Any previous feedback
        
        Returns:
            Instructions to pass to generator for regeneration
        """
        instructions = f"""
The previous version received the following feedback:
{feedback_text}

Previous content:
---
{content[:500]}...
---

Please regenerate the content incorporating this feedback:
- Address all points raised in the feedback
- Maintain fidelity to source material
- Improve areas highlighted in the feedback
- Keep similar structure but refine content

"""
        
        if previous_feedback:
            instructions += f"\nPrevious improvements requested: {previous_feedback}\n"
        
        return instructions
    
    @staticmethod
    async def update_feedback_history(
        content_id: str,
        new_feedback: str,
        db: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """
        Get history of all feedback for a content piece
        
        Args:
            content_id: Content ID
            new_feedback: New feedback to add
            db: Database session
        
        Returns:
            Full feedback history
        """
        try:
            query = select(FeedbackRecord).where(
                FeedbackRecord.content_id == content_id
            ).order_by(FeedbackRecord.timestamp)
            
            result = await db.execute(query)
            records = result.scalars().all()
            
            history = [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "feedback": r.feedback,
                    "status": r.status,
                    "editor": r.editor_name,
                }
                for r in records
            ]
            
            return history
            
        except Exception as e:
            logger.warning(f"Could not retrieve feedback history: {e}")
            return []
