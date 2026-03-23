"""
Feedback API - Standalone endpoint for submitting teacher feedback
Persists feedback records and triggers learning pipeline updates.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.services.feedback_learning_service import FeedbackLearningService
from app.schemas import FeedbackSubmit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _get_user_id(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    payload = decode_token(authorization.removeprefix("Bearer "))
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return str(user_id)


@router.post("/{content_id}")
async def submit_feedback(
    content_id: str,
    data: FeedbackSubmit,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit teacher feedback on a piece of generated content.

    The feedback is persisted for:
    - Auditing purposes
    - Few-shot prompting in future generation calls
    - Triggering regeneration when status is ``needs_revision`` or ``rejected``

    Args:
        content_id: ID of the ``GeneratedContent`` record being reviewed.
        data: Feedback payload (text, status, editor_name).

    Returns:
        Dict with the new feedback record ID and recommended next action.
    """
    _get_user_id(authorization)  # Auth check

    try:
        result = await FeedbackLearningService.record_feedback(
            db=db,
            content_id=content_id,
            feedback_text=data.feedback,
            status=data.status,
            editor_name=data.editor_name,
        )
        logger.info(f"Feedback submitted for content {content_id}: {data.status}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error submitting feedback for content {content_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
