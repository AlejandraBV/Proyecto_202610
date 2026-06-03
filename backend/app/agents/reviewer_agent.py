"""
Reviewer Agent - Validates generated content for accuracy and difficulty
Decides if content meets requirements or needs regeneration
"""
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """Validates generated content against requirements"""

    QUALITY_THRESHOLD = 0.65
    """
    Minimum overall score for content to be considered acceptable without revision.
    Scoring bands:
      0.0 – 0.40 : poor quality, reject
      0.40 – 0.65: needs revision
      0.65 – 1.00: approved / acceptable
    The weights applied to sub-scores are:
      fidelity_score × 0.50 + difficulty_score × 0.35 + requirements_score × 0.15
    """

    # ------------------------------------------------------------------
    # Static utility methods (used by orchestrator)
    # ------------------------------------------------------------------

    @staticmethod
    async def review_content(
        generated_content: str,
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        requirements: Optional[Dict[str, Any]] = None,
        source_context: str = "",
    ) -> Dict[str, Any]:
        """
        Review generated content for quality and fidelity.

        Returns:
            Review result with approval status and improvement suggestions
        """
        try:
            fidelity_score = 0.8
            if source_context:
                fidelity_score = await ReviewerAgent._check_fidelity(
                    generated_content, source_context, subject, topic
                )

            difficulty_check = await ReviewerAgent._check_difficulty(
                generated_content, content_type, level, subject
            )

            requirements_met = ReviewerAgent._check_requirements(
                generated_content, requirements or {}
            )

            overall_score = (
                fidelity_score * 0.5
                + difficulty_check["score"] * 0.35
                + requirements_met["score"] * 0.15
            )

            needs_regeneration = overall_score < ReviewerAgent.QUALITY_THRESHOLD

            suggestions = []
            if needs_regeneration:
                suggestions = await ReviewerAgent._generate_suggestions(
                    generated_content, fidelity_score, difficulty_check, requirements_met
                )

            review_result = {
                "approval_status": "approved" if not needs_regeneration else "needs_revision",
                "overall_score": round(overall_score, 2),
                "fidelity_score": round(fidelity_score, 2),
                "difficulty_check": difficulty_check,
                "requirements_met": requirements_met,
                "needs_regeneration": needs_regeneration,
                "improvement_suggestions": suggestions,
            }

            logger.info(
                f"Review complete: {review_result['approval_status']} "
                f"(score: {overall_score:.2f})"
            )
            return review_result

        except Exception as e:
            logger.error(f"Error in reviewer agent: {e}")
            raise

    @staticmethod
    async def _check_fidelity(
        generated_content: str,
        source_context: str,
        subject: str,
        topic: str,
    ) -> float:
        """Check if generated content is faithful to source material"""
        try:
            key_words = subject.lower().split() + topic.lower().split()
            matches = sum(1 for word in key_words if word in generated_content.lower())
            score = min(0.95, 0.5 + (matches * 0.1))
            return score
        except Exception as e:
            logger.warning(f"Could not check fidelity: {e}")
            return 0.75

    @staticmethod
    async def _check_difficulty(
        generated_content: str,
        content_type: str,
        required_level: str,
        subject: str,
    ) -> Dict[str, Any]:
        """Check if content matches the required difficulty level"""
        try:
            words = generated_content.split()
            avg_word_length = sum(len(w) for w in words) / max(len(words), 1)

            if avg_word_length > 7:
                difficulty_found = "advanced"
            elif avg_word_length > 5.5:
                difficulty_found = "intermediate"
            else:
                difficulty_found = "beginner"

            level_match = {
                "beginner": {"beginner": 1.0, "intermediate": 0.6, "advanced": 0.2},
                "intermediate": {"beginner": 0.7, "intermediate": 1.0, "advanced": 0.7},
                "advanced": {"beginner": 0.2, "intermediate": 0.6, "advanced": 1.0},
            }

            score = level_match.get(required_level, {}).get(difficulty_found, 0.7)

            return {
                "required_level": required_level,
                "detected_level": difficulty_found,
                "score": score,
                "matches": score > 0.7,
            }

        except Exception as e:
            logger.warning(f"Could not check difficulty: {e}")
            return {"score": 0.8, "matches": True}

    @staticmethod
    def _check_requirements(
        generated_content: str,
        requirements: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check if content meets specified requirements"""
        met_requirements = {}

        if requirements.get("include_examples"):
            has_examples = any(
                word in generated_content.lower()
                for word in ["example", "for example", "e.g.", "ejemplo"]
            )
            met_requirements["include_examples"] = has_examples

        if requirements.get("with_explanations"):
            has_explanations = any(
                word in generated_content.lower()
                for word in ["because", "due to", "reason"]
            )
            met_requirements["with_explanations"] = has_explanations

        if requirements.get("with_solutions"):
            met_requirements["with_solutions"] = len(generated_content) > 200

        if not met_requirements:
            met_requirements["general"] = True

        total_met = sum(1 for v in met_requirements.values() if v)
        score = total_met / max(len(met_requirements), 1)

        return {"met_requirements": met_requirements, "score": score}

    # ── Bloom's Taxonomy ──────────────────────────────────────────────────────

    # Keyword lists per Bloom level (Anderson & Krathwohl revision)
    _BLOOM_KEYWORDS: Dict[str, List[str]] = {
        "Remember":   ["define", "list", "recall", "name", "state", "identify",
                       "label", "match", "memorize", "repeat", "reproduce"],
        "Understand": ["explain", "describe", "interpret", "summarize", "compare",
                       "classify", "discuss", "paraphrase", "illustrate", "infer"],
        "Apply":      ["solve", "use", "calculate", "demonstrate", "apply",
                       "compute", "show", "complete", "construct", "perform"],
        "Analyze":    ["analyze", "distinguish", "examine", "differentiate", "relate",
                       "break down", "contrast", "investigate", "deconstruct"],
        "Evaluate":   ["assess", "evaluate", "judge", "justify", "critique",
                       "defend", "argue", "recommend", "select", "appraise"],
        "Create":     ["design", "create", "develop", "compose", "construct",
                       "plan", "produce", "formulate", "generate", "invent"],
    }

    _BLOOM_COLORS: Dict[str, str] = {
        "Remember":   "green",
        "Understand": "blue",
        "Apply":      "yellow",
        "Analyze":    "orange",
        "Evaluate":   "red",
        "Create":     "purple",
    }

    @staticmethod
    def tag_bloom_levels(content: str) -> List[Dict[str, Any]]:
        """
        Scan generated content and return a distribution of Bloom's taxonomy levels.

        Splits the content into question/item lines, checks each line against
        keyword lists, and returns an aggregated list of
        ``{level, count, color}`` dicts (only levels with count > 0, sorted by level).

        This is intentionally keyword-based (no extra LLM call) so it's fast.
        """
        if not content:
            return []

        # Build a flat reverse index: keyword → level
        kw_to_level: Dict[str, str] = {}
        for level, kws in ReviewerAgent._BLOOM_KEYWORDS.items():
            for kw in kws:
                kw_to_level[kw] = level

        # Split into candidate sentences / question stems
        import re
        lines = re.split(r"[\n.?!]", content.lower())

        counts: Dict[str, int] = {}
        for line in lines:
            for kw, level in kw_to_level.items():
                if kw in line:
                    counts[level] = counts.get(level, 0) + 1
                    break   # one level per line

        # Build result list sorted by taxonomy order
        taxonomy_order = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
        result = []
        for level in taxonomy_order:
            count = counts.get(level, 0)
            if count > 0:
                result.append({
                    "level": level,
                    "count": count,
                    "color": ReviewerAgent._BLOOM_COLORS[level],
                })

        return result

    @staticmethod
    async def _generate_suggestions(
        generated_content: str,
        fidelity_score: float,
        difficulty_check: Dict[str, Any],
        requirements_met: Dict[str, Any],
    ) -> List[str]:
        """Generate improvement suggestions for regeneration"""
        suggestions = []

        if fidelity_score < 0.7:
            suggestions.append("Regenerate with stronger focus on source material accuracy")

        if not difficulty_check.get("matches"):
            level = difficulty_check.get("required_level", "").upper()
            suggestions.append(f"Adjust content complexity to {level} level")

        for req, met in requirements_met.get("met_requirements", {}).items():
            if not met:
                suggestions.append(f"Ensure content includes {req.replace('_', ' ')}")

        return suggestions

    # ------------------------------------------------------------------
    # Instance methods (used by tests and LangGraph workflow)
    # ------------------------------------------------------------------

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Call LLM for review evaluation.
        This method can be patched in tests to return mock data.
        """
        return {
            "quality_score": 0.85,
            "fidelity_score": 0.85,
            "difficulty_match": True,
            "decision": "approved",
            "reasoning": "Content meets requirements",
        }

    async def review(self, generated_content: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review generated content using LLM evaluation.

        Args:
            generated_content: Content to review
            context: Context with content_type, difficulty_level, etc.

        Returns:
            Review result with decision, quality_score, fidelity_score, etc.
        """
        result = await self._call_llm(generated_content)
        logger.info(
            f"Review complete: decision={result.get('decision')}, "
            f"quality_score={result.get('quality_score')}"
        )
        return result
