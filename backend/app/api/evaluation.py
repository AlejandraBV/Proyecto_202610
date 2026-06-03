"""
RAGAS Evaluation API — compute quality metrics per conversation.

Endpoints:
  GET /conversations/{conversation_id}/evaluate
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import Conversation, Message
from app.services.evaluation_service import evaluate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["evaluation"])


def _user_from_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    payload = decode_token(authorization.removeprefix("Bearer "))
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return str(payload["sub"])


@router.get("/{conversation_id}/evaluate")
async def evaluate_conversation(
    conversation_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Compute RAGAS-style quality metrics for all assistant turns in a conversation.

    Returns per-turn scores and conversation-level averages:
      • faithfulness      — content grounded in source material
      • answer_relevance  — content addresses the user's query
      • context_precision — retrieved context was relevant & used
      • overall           — weighted average
    """
    user_id = _user_from_token(authorization)

    conv_res = await db.execute(
        select(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conv = conv_res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs_res = await db.execute(
        select(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)
    )
    messages: List[Message] = msgs_res.scalars().all()

    # Pair each assistant message with its preceding user message
    turn_scores: List[Dict[str, Any]] = []
    prev_user_content = ""
    for msg in messages:
        if msg.role == "user":
            prev_user_content = msg.content or ""
        elif msg.role == "assistant" and prev_user_content:
            scores = evaluate(
                user_query=prev_user_content,
                generated_content=msg.content or "",
                retrieved_context=None,   # context not stored on Message; use None
            )
            turn_scores.append({
                "message_id": msg.id,
                "user_query_preview": prev_user_content[:80],
                "response_preview": (msg.content or "")[:80],
                **scores,
            })

    if not turn_scores:
        return {
            "conversation_id": conversation_id,
            "turns": [],
            "averages": {
                "faithfulness": 0.0,
                "answer_relevance": 0.0,
                "context_precision": 0.0,
                "overall": 0.0,
            },
        }

    n = len(turn_scores)
    averages = {
        "faithfulness":      round(sum(t["faithfulness"] for t in turn_scores) / n, 3),
        "answer_relevance":  round(sum(t["answer_relevance"] for t in turn_scores) / n, 3),
        "context_precision": round(sum(t["context_precision"] for t in turn_scores) / n, 3),
        "overall":           round(sum(t["overall"] for t in turn_scores) / n, 3),
    }

    return {
        "conversation_id": conversation_id,
        "turns": turn_scores,
        "averages": averages,
    }
