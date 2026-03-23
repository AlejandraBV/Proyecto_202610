"""
RAG Service - Retrieval-Augmented Generation with semantic search and re-ranking
Wraps ChromaDB queries and applies a lightweight cross-encoder re-ranking step.
"""
import logging
from typing import List, Dict, Any, Optional

from app.services.vector_service import VectorDatabaseService

logger = logging.getLogger(__name__)


class RAGService:
    """
    Retrieval service that fetches candidate chunks from ChromaDB and optionally
    re-ranks them by relevance before returning the top-k results.
    """

    DEFAULT_CANDIDATE_MULTIPLIER = 3  # Fetch this many more candidates for re-ranking

    @classmethod
    async def retrieve(
        cls,
        query: str,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: int = 5,
        rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most relevant document chunks for *query*.

        Steps:
        1. Query ChromaDB for ``top_k * candidate_multiplier`` candidates.
        2. If re-ranking is requested, score candidates with a simple
           keyword-overlap heuristic (a full cross-encoder can be plugged in
           here when the environment supports it).
        3. Return the top ``top_k`` results sorted by relevance.

        Args:
            query: User query or generation prompt.
            subject: Filter results to this subject.
            topic: Filter results to this topic.
            top_k: Number of results to return.
            rerank: Whether to apply the re-ranking step.

        Returns:
            List of dicts with keys: id, content, metadata, distance, score.
        """
        candidate_count = top_k * cls.DEFAULT_CANDIDATE_MULTIPLIER if rerank else top_k

        # Build metadata filters
        where: Optional[Dict[str, Any]] = None
        conditions: List[Dict[str, str]] = []
        if subject:
            conditions.append({"subject": subject})
        if topic:
            conditions.append({"topic": topic})
        if len(conditions) == 1:
            where = conditions[0]
        elif len(conditions) > 1:
            where = {"$and": conditions}

        raw = await VectorDatabaseService.query(
            query_text=query,
            n_results=candidate_count,
            where=where,
        )

        candidates: List[Dict[str, Any]] = raw.get("results", [])

        if not candidates:
            return []

        if rerank:
            candidates = cls._rerank(query, candidates)

        return candidates[:top_k]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rerank(query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Lightweight re-ranking based on query-term overlap.

        Each candidate receives a score combining:
        - Term overlap ratio with the query (Jaccard-like)
        - Inverted ChromaDB distance (lower distance → higher relevance)

        When a proper cross-encoder model is available it can replace this
        function without changing any caller code.
        """
        query_terms = set(query.lower().split())

        scored: List[Dict[str, Any]] = []
        for cand in candidates:
            content_terms = set(cand.get("content", "").lower().split())
            overlap = len(query_terms & content_terms) / max(len(query_terms), 1)
            distance = cand.get("distance", 1.0)
            # distance is in [0, 2] for cosine space; lower is better
            similarity = max(0.0, 1.0 - distance)
            combined_score = 0.5 * overlap + 0.5 * similarity
            scored.append({**cand, "score": round(combined_score, 4)})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored
