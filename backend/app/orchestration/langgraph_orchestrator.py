"""
LangGraph-based content generation pipeline.

StateGraph flow:
    fetch_context → analyze → generate → review
                                  ↑          |
                                  └──────────┘  (if needs_regeneration)
                                             ↓  (if approved / max attempts)
                                       build_result → END
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from app.agents.analyzer_agent import AnalyzerAgent
from app.agents.feedback_agent import FeedbackAgent
from app.agents.generator_agent import GeneratorAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── State definition ──────────────────────────────────────────────────────────

class ContentState(TypedDict):
    # ── Inputs (set before invocation) ──────────────────────────────────────
    conversation_id: str
    user_prompt: str
    subject: str
    topic: str
    level: str
    user_id: Optional[str]
    document_context: Optional[str]
    document_id: Optional[str]
    db: Any                       # AsyncSession — kept in-memory, not serialised
    max_attempts: int
    previous_feedback: List[Any]

    # ── Computed during execution ─────────────────────────────────────────────
    feedback_examples: List[Any]
    analysis: Optional[Dict[str, Any]]
    generated_content: Optional[str]
    review: Optional[Dict[str, Any]]
    improvement_instructions: str
    attempt_count: int

    # ── Output ────────────────────────────────────────────────────────────────
    result: Optional[Dict[str, Any]]


# ── Node implementations ──────────────────────────────────────────────────────

async def fetch_context_node(state: ContentState) -> Dict[str, Any]:
    """
    Load optional document content from the DB and historical feedback
    examples for few-shot prompting.
    """
    document_context: Optional[str] = state.get("document_context")
    document_id: Optional[str] = state.get("document_id")
    db: Any = state.get("db")
    user_id: Optional[str] = state.get("user_id")
    subject: str = state["subject"]
    topic: str = state["topic"]

    # Load document if needed
    if document_id and not document_context and db is not None:
        try:
            from sqlalchemy.future import select
            from app.models.models import Document

            result = await db.execute(select(Document).filter(Document.id == document_id))
            doc = result.scalar_one_or_none()
            if doc and doc.original_content:
                document_context = doc.original_content
                logger.info(
                    "[fetch_context] Loaded document '%s' (%d chars)",
                    doc.filename,
                    len(document_context),
                )
        except Exception as exc:
            logger.warning("[fetch_context] Could not load document %s: %s", document_id, exc)

    # Load few-shot feedback examples
    feedback_examples: List[Any] = []
    if user_id and db:
        try:
            feedback_examples = await FeedbackAgent.get_learning_examples(
                user_id=user_id,
                content_type="text",   # placeholder; updated after analyze node
                subject=subject,
                db=db,
                limit=3,
            )
        except Exception as exc:
            logger.warning("[fetch_context] Could not load feedback examples: %s", exc)

    return {
        "document_context": document_context,
        "feedback_examples": feedback_examples,
    }


async def analyze_node(state: ContentState) -> Dict[str, Any]:
    """Run AnalyzerAgent: detect content type, difficulty, retrieve RAG context."""
    analysis = await AnalyzerAgent.analyze_with_context(
        user_prompt=state["user_prompt"],
        subject=state["subject"],
        topic=state["topic"],
        document_context=state.get("document_context"),
        user_level=state["level"],
    )
    logger.info(
        "[analyze] type=%s difficulty=%s",
        analysis["content_type"],
        analysis["difficulty_level"],
    )
    return {"analysis": analysis}


async def generate_node(state: ContentState) -> Dict[str, Any]:
    """Run GeneratorAgent: produce content (incorporating improvement feedback)."""
    analysis: Dict[str, Any] = state["analysis"]  # type: ignore[assignment]
    attempt: int = state.get("attempt_count", 0) + 1
    improvement: str = state.get("improvement_instructions", "")
    prompt: str = state["user_prompt"] + improvement

    generated = await GeneratorAgent.generate(
        content_type=analysis["content_type"],
        subject=state["subject"],
        topic=state["topic"],
        level=analysis["difficulty_level"],
        user_prompt=prompt,
        retrieved_context=analysis["retrieved_context"],
        feedback_examples=state.get("feedback_examples", []),
        requirements=analysis["requirements"],
    )

    logger.info("[generate] attempt %d — %d chars produced", attempt, len(generated))
    return {"generated_content": generated, "attempt_count": attempt}


async def review_node(state: ContentState) -> Dict[str, Any]:
    """Run ReviewerAgent: score quality and optionally request improvements."""
    analysis: Dict[str, Any] = state["analysis"]  # type: ignore[assignment]
    generated: str = state.get("generated_content") or ""

    review = await ReviewerAgent.review_content(
        generated_content=generated,
        content_type=analysis["content_type"],
        subject=state["subject"],
        topic=state["topic"],
        level=analysis["difficulty_level"],
        requirements=analysis["requirements"],
        source_context=state.get("document_context") or analysis["retrieved_context"],
    )

    improvement = ""
    if review.get("needs_regeneration") and review.get("improvement_suggestions"):
        improvement = "\n\nImprovement feedback:\n" + "\n".join(
            review["improvement_suggestions"]
        )

    logger.info(
        "[review] status=%s score=%.2f attempt=%d",
        review["approval_status"],
        review["overall_score"],
        state.get("attempt_count", 1),
    )
    return {"review": review, "improvement_instructions": improvement}


def should_regenerate(state: ContentState) -> Literal["generate", "__end__"]:
    """
    Routing function executed after each review pass.

    Returns:
        "generate"  → loop back for another generation attempt
        END         → proceed to build_result node
    """
    review: Dict[str, Any] = state.get("review") or {}
    attempt: int = state.get("attempt_count", 1)
    max_attempts: int = state.get("max_attempts", 3)

    needs_regen: bool = review.get("needs_regeneration", False)

    if not needs_regen:
        return END                                   # type: ignore[return-value]
    if max_attempts > 0 and attempt >= max_attempts:
        logger.info("[route] max attempts (%d) reached — using best result so far", max_attempts)
        return END                                   # type: ignore[return-value]

    return "generate"


async def build_result_node(state: ContentState) -> Dict[str, Any]:
    """Assemble the final result dictionary from accumulated state."""
    analysis: Dict[str, Any] = state.get("analysis") or {}
    review: Dict[str, Any] = state.get("review") or {}
    previous_feedback: List[Any] = state.get("previous_feedback") or []

    # Append Bloom taxonomy tags from the reviewer
    bloom_distribution = ReviewerAgent.tag_bloom_levels(
        state.get("generated_content") or ""
    )

    result: Dict[str, Any] = {
        "conversation_id": state["conversation_id"],
        "content": state.get("generated_content") or "",
        "content_type": analysis.get("content_type", "text"),
        "subject": state["subject"],
        "topic": state["topic"],
        "level": analysis.get("difficulty_level", state["level"]),
        "status": "generated",
        "version": len(previous_feedback) + 1,
        "analysis": analysis,
        "review": review,
        "generation_attempts": state.get("attempt_count", 1),
        "analysis_confidence": analysis.get("analysis_confidence", 0.85),
        "review_score": review.get("overall_score", 0.75),
        "bloom_tags": bloom_distribution,
    }
    return {"result": result}


# ── Graph construction ─────────────────────────────────────────────────────────

def _build_graph():
    graph: StateGraph = StateGraph(ContentState)

    graph.add_node("fetch_context", fetch_context_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("generate", generate_node)
    graph.add_node("review", review_node)
    graph.add_node("build_result", build_result_node)

    graph.set_entry_point("fetch_context")
    graph.add_edge("fetch_context", "analyze")
    graph.add_edge("analyze", "generate")
    graph.add_edge("generate", "review")
    graph.add_conditional_edges(
        "review",
        should_regenerate,
        {"generate": "generate", END: "build_result"},
    )
    graph.add_edge("build_result", END)

    return graph.compile()


_compiled_graph = None


def _get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


# ── Public entry point ────────────────────────────────────────────────────────

async def run_generation_pipeline(
    conversation_id: str,
    user_prompt: str,
    subject: str,
    topic: str,
    level: str,
    user_id: Optional[str] = None,
    document_context: Optional[str] = None,
    document_id: Optional[str] = None,
    previous_feedback: Optional[List[Any]] = None,
    db: Any = None,
) -> Dict[str, Any]:
    """
    Execute the LangGraph content-generation pipeline and return the result dict.

    This is a drop-in replacement for ``ContentOrchestrator.generate_with_rag_and_agents``.
    """
    initial_state: ContentState = {
        "conversation_id": conversation_id,
        "user_prompt": user_prompt,
        "subject": subject,
        "topic": topic,
        "level": level,
        "user_id": user_id,
        "document_context": document_context,
        "document_id": document_id,
        "db": db,
        "max_attempts": settings.MAX_GENERATION_ATTEMPTS or 3,
        "previous_feedback": previous_feedback or [],
        "feedback_examples": [],
        "analysis": None,
        "generated_content": None,
        "review": None,
        "improvement_instructions": "",
        "attempt_count": 0,
        "result": None,
    }

    graph = _get_graph()
    final_state: ContentState = await graph.ainvoke(initial_state)

    result = final_state.get("result")
    if result is None:
        raise RuntimeError("LangGraph pipeline completed without producing a result")

    logger.info(
        "LangGraph pipeline done: %d attempt(s), score=%.2f, version=%d",
        result["generation_attempts"],
        result["review_score"],
        result["version"],
    )
    return result
