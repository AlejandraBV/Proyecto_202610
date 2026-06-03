"""
Simplified RAGAS-style evaluation service.

Computes three metrics without requiring extra LLM calls:

  faithfulness     — word-overlap between generated content and source chunks
  answer_relevance — word-overlap between generated content and the user query
  context_precision — fraction of retrieved content used (unique key-term match)

All scores are in [0.0, 1.0].  Higher is better.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _tokenize(text: str) -> set:
    """Lowercase alphanumeric tokens, min length 3."""
    return {w for w in re.sub(r"[^\w\s]", "", text.lower()).split() if len(w) >= 3}


def evaluate(
    user_query: str,
    generated_content: str,
    retrieved_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute RAGAS-inspired metrics.

    Args:
        user_query:         The original user prompt.
        generated_content:  The assistant's generated response.
        retrieved_context:  Raw text of the retrieved chunks used during generation.

    Returns:
        {
            "faithfulness":      float,  # how much content is grounded in sources
            "answer_relevance":  float,  # how well the content addresses the query
            "context_precision": float,  # how focused the retrieved context is
            "overall":           float,  # weighted average
        }
    """
    q_tokens = _tokenize(user_query)
    a_tokens = _tokenize(generated_content)
    c_tokens = _tokenize(retrieved_context) if retrieved_context else set()

    # ── Answer Relevance ──────────────────────────────────────────────────────
    # Jaccard similarity between query and answer token sets.
    if q_tokens and a_tokens:
        ar_score = len(q_tokens & a_tokens) / len(q_tokens | a_tokens)
    else:
        ar_score = 0.0

    # ── Faithfulness ─────────────────────────────────────────────────────────
    # What fraction of answer tokens also appear in the context?
    if a_tokens and c_tokens:
        faith_score = len(a_tokens & c_tokens) / len(a_tokens)
    elif not c_tokens:
        # No context retrieved → neutral score (pure parametric knowledge)
        faith_score = 0.5
    else:
        faith_score = 0.0

    # ── Context Precision ─────────────────────────────────────────────────────
    # What fraction of context tokens are actually referenced in the answer?
    if c_tokens and a_tokens:
        cp_score = len(c_tokens & a_tokens) / len(c_tokens)
    elif not c_tokens:
        cp_score = 0.5
    else:
        cp_score = 0.0

    overall = (faith_score * 0.40 + ar_score * 0.35 + cp_score * 0.25)

    return {
        "faithfulness":      round(min(faith_score, 1.0), 3),
        "answer_relevance":  round(min(ar_score, 1.0), 3),
        "context_precision": round(min(cp_score, 1.0), 3),
        "overall":           round(min(overall, 1.0), 3),
    }
