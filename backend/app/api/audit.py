"""
Audit Trail API — returns a chronological log of all HITL events for a conversation.

Events included:
  • message_rating   — thumbs-up on an assistant message
  • refinement       — professor edited + AI refined a message
  • reclassification — subject label corrected by the professor
  • agent_decision   — analyzer / generator / reviewer decisions recorded during generation
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import (
    AgentDecisionRecord,
    ClassificationCorrection,
    Conversation,
    Message,
    MessageRating,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["audit"])


def _user_from_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    payload = decode_token(authorization.removeprefix("Bearer "))
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return str(payload["sub"])


@router.get("/{conversation_id}/audit")
async def get_audit_trail(
    conversation_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Return all HITL audit events for a conversation, sorted oldest → newest.

    Each event is a dict with at minimum:
      { "type": str, "timestamp": ISO-8601 str, ...type-specific fields... }
    """
    user_id = _user_from_token(authorization)

    # Verify ownership
    conv_res = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    if not conv_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    events: List[Dict[str, Any]] = []

    # ── Message ratings ───────────────────────────────────────────────────────
    msg_ids_res = await db.execute(
        select(Message.id).filter(Message.conversation_id == conversation_id)
    )
    msg_ids = [row[0] for row in msg_ids_res.all()]

    if msg_ids:
        ratings_res = await db.execute(
            select(MessageRating).filter(MessageRating.message_id.in_(msg_ids))
        )
        for r in ratings_res.scalars().all():
            events.append({
                "type": "message_rating",
                "timestamp": r.timestamp.isoformat(),
                "message_id": r.message_id,
                "rating": r.rating,
                "feedback_text": r.feedback_text,
            })

    # ── Classification corrections ────────────────────────────────────────────
    corr_res = await db.execute(
        select(ClassificationCorrection).filter(
            ClassificationCorrection.conversation_id == conversation_id
        )
    )
    for c in corr_res.scalars().all():
        events.append({
            "type": "reclassification",
            "timestamp": c.timestamp.isoformat(),
            "original_subject": c.original_subject,
            "corrected_subject": c.corrected_subject,
            "sample_prompt": c.sample_prompt,
        })

    # ── Agent decisions ───────────────────────────────────────────────────────
    decisions_res = await db.execute(
        select(AgentDecisionRecord).filter(
            AgentDecisionRecord.conversation_id == conversation_id
        )
    )
    for d in decisions_res.scalars().all():
        events.append({
            "type": "agent_decision",
            "timestamp": d.timestamp.isoformat(),
            "agent_name": d.agent_name,
            "decision": d.decision,
            "reasoning": d.reasoning,
            "quality_score": d.quality_score,
            "iteration": d.iteration,
        })

    # ── Refinement events (assistant messages that were edited) ───────────────
    # A refinement is detected when there are two consecutive assistant messages
    # (original + refined). We just log all assistant messages as content events.
    msgs_res = await db.execute(
        select(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == "assistant",
        )
        .order_by(Message.timestamp)
    )
    assistant_msgs = msgs_res.scalars().all()

    # Mark as "refinement" any assistant message that follows another one
    prev_was_assistant = False
    for msg in assistant_msgs:
        if prev_was_assistant:
            events.append({
                "type": "refinement",
                "timestamp": msg.timestamp.isoformat(),
                "message_id": msg.id,
                "content_preview": (msg.content or "")[:150],
            })
        prev_was_assistant = True

    # Sort all events by timestamp ascending
    events.sort(key=lambda e: e["timestamp"])
    return events
