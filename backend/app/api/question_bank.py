"""
Question Bank API — save, search, and reuse questions across exams.

Endpoints:
  GET    /questions                   list / search questions
  POST   /questions                   save a question
  GET    /questions/{id}              get one question
  PUT    /questions/{id}              update a question
  DELETE /questions/{id}              delete a question
  POST   /questions/extract/{msg_id}  auto-extract questions from an assistant message
"""
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import Conversation, Message, Question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["question-bank"])


def _user_from_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    payload = decode_token(authorization.removeprefix("Bearer "))
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return str(payload["sub"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    content: str
    answer: Optional[str] = None
    question_type: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    bloom_level: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    source_conversation_id: Optional[str] = None
    source_message_id: Optional[str] = None


class QuestionUpdate(BaseModel):
    content: Optional[str] = None
    answer: Optional[str] = None
    question_type: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    bloom_level: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None


class QuestionResponse(BaseModel):
    id: str
    content: str
    answer: Optional[str] = None
    question_type: Optional[str] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    bloom_level: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    times_used: int = 0
    source_conversation_id: Optional[str] = None
    source_message_id: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_obj(cls, q: Question) -> "QuestionResponse":
        tags_list = []
        if q.tags:
            try:
                tags_list = json.loads(q.tags)
            except Exception:
                tags_list = [q.tags]
        return cls(
            id=q.id,
            content=q.content,
            answer=q.answer,
            question_type=q.question_type,
            subject=q.subject,
            topic=q.topic,
            bloom_level=q.bloom_level,
            difficulty=q.difficulty,
            tags=tags_list,
            times_used=q.times_used or 0,
            source_conversation_id=q.source_conversation_id,
            source_message_id=q.source_message_id,
            created_at=q.created_at.isoformat(),
            updated_at=q.updated_at.isoformat(),
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_questions_from_text(text: str) -> List[str]:
    """
    Heuristic extraction of numbered questions from markdown/plain text.
    Matches lines like:  "1. Question text"  or  "**1.** Question"
    """
    pattern = re.compile(
        r"(?:^|\n)\s*(?:\*{0,2})\s*(\d+)[.)]\s*(?:\*{0,2})\s*(.+?)(?=\n\s*\d+[.)]|\Z)",
        re.DOTALL,
    )
    results = []
    for m in pattern.finditer(text):
        q = m.group(2).strip()
        # Remove trailing markdown artifacts
        q = re.sub(r"\*{1,2}$", "", q).strip()
        if q:
            results.append(q)
    return results


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=List[QuestionResponse])
async def list_questions(
    subject: Optional[str] = Query(default=None),
    topic: Optional[str] = Query(default=None),
    bloom_level: Optional[str] = Query(default=None),
    difficulty: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None, description="Full-text search in content"),
    limit: int = Query(default=50, le=200),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> List[QuestionResponse]:
    """List / search questions in the bank."""
    user_id = _user_from_token(authorization)

    query = select(Question).filter(Question.user_id == user_id)

    if subject:
        query = query.filter(Question.subject.ilike(f"%{subject}%"))
    if topic:
        query = query.filter(Question.topic.ilike(f"%{topic}%"))
    if bloom_level:
        query = query.filter(Question.bloom_level == bloom_level)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if q:
        query = query.filter(Question.content.ilike(f"%{q}%"))

    query = query.order_by(Question.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return [QuestionResponse.from_orm_obj(row) for row in result.scalars().all()]


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    data: QuestionCreate,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    """Save a question to the bank."""
    user_id = _user_from_token(authorization)

    q = Question(
        id=str(uuid.uuid4()),
        user_id=user_id,
        content=data.content,
        answer=data.answer,
        question_type=data.question_type,
        subject=data.subject,
        topic=data.topic,
        bloom_level=data.bloom_level,
        difficulty=data.difficulty,
        tags=json.dumps(data.tags or []),
        source_conversation_id=data.source_conversation_id,
        source_message_id=data.source_message_id,
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    logger.info("Question %s saved for user %s", q.id, user_id)
    return QuestionResponse.from_orm_obj(q)


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    user_id = _user_from_token(authorization)
    result = await db.execute(
        select(Question).filter(Question.id == question_id, Question.user_id == user_id)
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return QuestionResponse.from_orm_obj(q)


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: str,
    data: QuestionUpdate,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> QuestionResponse:
    user_id = _user_from_token(authorization)
    result = await db.execute(
        select(Question).filter(Question.id == question_id, Question.user_id == user_id)
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    if data.content is not None:
        q.content = data.content
    if data.answer is not None:
        q.answer = data.answer
    if data.question_type is not None:
        q.question_type = data.question_type
    if data.subject is not None:
        q.subject = data.subject
    if data.topic is not None:
        q.topic = data.topic
    if data.bloom_level is not None:
        q.bloom_level = data.bloom_level
    if data.difficulty is not None:
        q.difficulty = data.difficulty
    if data.tags is not None:
        q.tags = json.dumps(data.tags)

    await db.commit()
    await db.refresh(q)
    return QuestionResponse.from_orm_obj(q)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    user_id = _user_from_token(authorization)
    result = await db.execute(
        select(Question).filter(Question.id == question_id, Question.user_id == user_id)
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    await db.delete(q)
    await db.commit()


@router.post("/extract/{message_id}", response_model=List[QuestionResponse])
async def extract_questions_from_message(
    message_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> List[QuestionResponse]:
    """
    Auto-extract numbered questions from an assistant message and save them
    to the question bank.  Returns the list of saved questions.
    """
    user_id = _user_from_token(authorization)

    # Fetch message + verify ownership via conversation
    msg_res = await db.execute(
        select(Message).filter(Message.id == message_id, Message.role == "assistant")
    )
    msg = msg_res.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    conv_res = await db.execute(
        select(Conversation).filter(
            Conversation.id == msg.conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conv = conv_res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=403, detail="Not authorized")

    extracted = _extract_questions_from_text(msg.content or "")
    if not extracted:
        raise HTTPException(
            status_code=422,
            detail="No numbered questions found in message. Use the manual save instead.",
        )

    # Detect Bloom level per question using keyword analysis
    from app.agents.reviewer_agent import ReviewerAgent

    saved: List[QuestionResponse] = []
    for qtext in extracted:
        bloom_dist = ReviewerAgent.tag_bloom_levels(qtext)
        bloom_level = bloom_dist[0]["level"] if bloom_dist else None

        q = Question(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=qtext,
            subject=conv.primary_subject or conv.subject,
            topic=conv.primary_topic or conv.topic,
            bloom_level=bloom_level,
            difficulty=msg.detected_content_type or "intermediate",
            source_conversation_id=conv.id,
            source_message_id=msg.id,
            tags=json.dumps([conv.primary_subject or "general"]),
        )
        db.add(q)
        saved.append(q)

    await db.commit()
    for s in saved:
        await db.refresh(s)

    logger.info("Extracted %d questions from message %s", len(saved), message_id)
    return [QuestionResponse.from_orm_obj(s) for s in saved]
