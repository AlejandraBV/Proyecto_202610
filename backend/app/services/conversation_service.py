"""
Conversation Service - CRUD operations for conversations and messages
"""
import json
import re
import uuid
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.models import (
    Conversation, Document, Message, GeneratedContent, Folder,
    ClassificationCorrection,
)

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

    # Minimum similarity (0–1) required to route a message into an existing
    # conversation instead of creating a new one.
    # 0.45 means an exact subject match alone (0.50) is enough to continue,
    # while a completely different subject+topic pair (0.0) always splits.
    SIMILARITY_THRESHOLD: float = 0.45

    @staticmethod
    def _topic_similarity(
        subject1: str, topic1: str,
        subject2: str, topic2: str,
    ) -> float:
        """
        Compute a 0.0–1.0 similarity score for two subject/topic pairs.

        Scoring:
          Subject match (exact)     → +0.50
          Subject match (partial)   → +0.30
          Topic word Jaccard        → +0.50 * jaccard

        A score >= SIMILARITY_THRESHOLD means the message likely belongs to an
        existing conversation rather than needing a brand-new one.
        """
        score = 0.0

        s1 = (subject1 or "").strip().lower()
        s2 = (subject2 or "").strip().lower()

        if s1 and s2:
            if s1 == s2:
                score += 0.50
            elif s1 in s2 or s2 in s1:
                score += 0.30  # e.g. "Geology" ↔ "Earth Sciences"

        t1 = (topic1 or "").strip().lower()
        t2 = (topic2 or "").strip().lower()

        if t1 and t2:
            # Tokenise: keep only alphanumeric words, length ≥ 3
            tok1 = set(w for w in re.sub(r"[^\w\s]", "", t1).split() if len(w) >= 3)
            tok2 = set(w for w in re.sub(r"[^\w\s]", "", t2).split() if len(w) >= 3)
            if tok1 or tok2:
                intersection = tok1 & tok2
                union = tok1 | tok2
                jaccard = len(intersection) / len(union) if union else 0.0
                score += jaccard * 0.50

        return min(score, 1.0)

    @staticmethod
    async def process_message_and_route(
        user_id: str,
        user_prompt: str,
        db: AsyncSession,
        conversation_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect topic from prompt + optional document and decide where the
        message belongs.

        Routing rules (in priority order)
        ──────────────────────────────────
        A. conversation_id is None  →  user explicitly started a NEW chat.
           Always create a new conversation.  Never search history.

        B. conversation_id is set  →  user is inside an existing conversation.
           Compare the detected topic against THAT conversation only:
             • Similar enough (score >= SIMILARITY_THRESHOLD): stay in it.
             • Different topic: create a new conversation.
           We intentionally do NOT search other existing conversations —
           that would silently redirect the user somewhere they didn't go.

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

        # ── 1. Document metadata (takes precedence over prompt) ───────────
        doc_metadata: Optional[Dict[str, Any]] = None
        if document_id:
            doc_metadata = await ConversationService._get_document_metadata(
                document_id, db
            )

        # ── 1b. Load recent user corrections for few-shot learning ────────
        # We fetch up to 10 most-recent corrections for this user and pass
        # them to hybrid_detect → _llm_detect so the classifier progressively
        # learns each user's preferred subject vocabulary without retraining.
        recent_corrections: Optional[list] = None
        try:
            corr_result = await db.execute(
                select(ClassificationCorrection)
                .filter(ClassificationCorrection.user_id == user_id)
                .order_by(ClassificationCorrection.timestamp.desc())
                .limit(10)
            )
            rows = corr_result.scalars().all()
            if rows:
                recent_corrections = [
                    {
                        "sample": c.sample_prompt or "",
                        "original_subject": c.original_subject or "",
                        "corrected_subject": c.corrected_subject,
                    }
                    for c in rows
                ]
                logger.debug(
                    "Loaded %d user corrections for few-shot injection", len(rows)
                )
        except Exception as exc:
            logger.warning("Could not load classification corrections: %s", exc)

        # ── 2. Detect subject / topic ─────────────────────────────────────
        detected = await MetadataAnalyzer.hybrid_detect(
            user_prompt,
            document_metadata=doc_metadata,
            corrections=recent_corrections,
        )
        new_subject = detected.get("subject") or ""
        new_topic = detected.get("topic") or ""

        # ── 3. Route ──────────────────────────────────────────────────────

        # Case A: no active conversation → user chose "New Chat" → always new
        if conversation_id is None:
            is_new = True
            logger.info(
                "No active conversation → creating new chat for '%s / %s'",
                new_subject or "General", new_topic or "Untitled",
            )

        # Case B: user is inside an existing conversation.
        #
        # Routing rules (in priority order):
        #
        #  1. No subject detected (follow-ups, refinements, commands like
        #     "make it harder", "add 5 more questions", "explain part 2") →
        #     always CONTINUE in the current conversation.  These messages have
        #     no independent topic; they only make sense as continuations.
        #
        #  2. Same subject detected → CONTINUE (topic may deepen but area is the same).
        #
        #  3. Clearly different subject detected with high confidence →
        #     CREATE a new conversation so the topics don't pollute each other.
        #
        # The user can always click "New Chat" to start fresh regardless of topic.
        else:
            result = await db.execute(
                select(Conversation).filter(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            current_conv = result.scalar_one_or_none()

            if current_conv is None:
                # Conversation was deleted or doesn't belong to this user.
                is_new = True
                conversation_id = None
                logger.warning(
                    "Conversation %s not found; creating new.", conversation_id
                )
            else:
                cur_subject = current_conv.primary_subject or current_conv.subject or ""
                cur_topic   = current_conv.primary_topic   or current_conv.topic   or ""

                if not new_subject:
                    # Rule 1: no subject detected → follow-up / refinement → continue.
                    is_new = False
                    detected["subject"] = cur_subject
                    detected["topic"]   = cur_topic
                    logger.info(
                        "No subject detected — treating as follow-up, "
                        "continuing conversation %s ('%s / %s')",
                        conversation_id, cur_subject, cur_topic,
                    )
                else:
                    # Rule 2 / 3: compare detected subject against current.
                    score = ConversationService._topic_similarity(
                        new_subject, new_topic, cur_subject, cur_topic
                    )

                    if score >= ConversationService.SIMILARITY_THRESHOLD:
                        # Rule 2: same/similar topic → continue.
                        is_new = False
                        if not new_topic:
                            detected["topic"] = cur_topic
                        logger.info(
                            "Continuing conversation %s (score=%.2f) — "
                            "'%s / %s' ≈ '%s / %s'",
                            conversation_id, score,
                            new_subject, new_topic, cur_subject, cur_topic,
                        )
                    else:
                        # Rule 3: different subject detected → new conversation.
                        is_new = True
                        logger.info(
                            "Topic changed (score=%.2f < %.2f): '%s / %s' → '%s / %s' "
                            "— creating new conversation",
                            score, ConversationService.SIMILARITY_THRESHOLD,
                            cur_subject, cur_topic, new_subject, new_topic,
                        )

        # ── 4. Create new conversation when needed ────────────────────────
        if is_new:
            subject = new_subject or "General"
            topic = new_topic or "Untitled"
            title = f"{subject} - {topic}"

            folder_id = await ConversationService._get_or_create_subject_folder(
                db=db, user_id=user_id, subject=subject
            )

            new_conv = Conversation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=title,
                subject=subject,
                topic=topic,
                primary_subject=subject,
                primary_topic=topic,
                folder_id=folder_id,
            )
            db.add(new_conv)
            await db.commit()
            await db.refresh(new_conv)
            conversation_id = new_conv.id
            logger.info(
                "Created new conversation %s for '%s / %s'",
                conversation_id, subject, topic,
            )

        return {
            "conversation_id": conversation_id,
            "is_new_conversation": is_new,
            "subject": detected.get("subject"),
            "topic": detected.get("topic"),
            "content_type": detected.get("content_type"),
            "confidence": detected.get("confidence", 0.0),
            "detection_method": detected.get("method"),
        }

    # Color palette for auto-created subject folders
    SUBJECT_COLORS: Dict[str, str] = {
        "Biology": "#10B981",
        "Chemistry": "#F59E0B",
        "Physics": "#3B82F6",
        "Mathematics": "#EF4444",
        "History": "#8B5CF6",
        "Literature": "#EC4899",
        "Geography": "#06B6D4",
        "Economics": "#6366F1",
        "General": "#64748B",
    }

    SUBJECT_ICONS: Dict[str, str] = {
        "Biology": "🧬",
        "Chemistry": "⚗️",
        "Physics": "⚛️",
        "Mathematics": "🔢",
        "History": "📚",
        "Literature": "📖",
        "Geography": "🌍",
        "Economics": "📈",
        "General": "💡",
    }

    @staticmethod
    async def _get_or_create_subject_folder(
        db: AsyncSession,
        user_id: str,
        subject: str,
    ) -> Optional[str]:
        """Find or create a folder for a given subject. Returns the folder ID."""
        # Never auto-create a catch-all "General" folder — let those chats be uncategorized
        if not subject or subject.strip().lower() == "general":
            return None

        # Fetch all user folders once for fuzzy matching
        all_result = await db.execute(
            select(Folder).filter(Folder.user_id == user_id)
        )
        all_folders = all_result.scalars().all()

        subject_lower = subject.strip().lower()

        # 1. Exact match
        for f in all_folders:
            if f.name.lower() == subject_lower:
                return f.id

        # 2. Fuzzy match: existing folder name contains subject OR subject contains folder name
        #    e.g. "Earth Sciences" folder matches detected subject "Geology"
        for f in all_folders:
            f_lower = f.name.lower()
            if f_lower in subject_lower or subject_lower in f_lower:
                return f.id

        # 3. Create a new folder
        color = ConversationService.SUBJECT_COLORS.get(subject, "#64748B")
        icon = ConversationService.SUBJECT_ICONS.get(subject, "📝")

        new_folder = Folder(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=subject,
            description=f"Conversations about {subject}",
            color=color,
            icon=icon,
        )
        db.add(new_folder)
        await db.flush()  # get the id without full commit
        return new_folder.id

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

        detected = await MetadataAnalyzer.hybrid_detect(document.original_content)
        return {
            "subject": detected.get("subject"),
            "topic": detected.get("topic"),
        }
