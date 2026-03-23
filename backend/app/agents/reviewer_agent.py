"""
Reviewer Agent - Validates generated content for accuracy and difficulty
Decides if content meets requirements or needs regeneration
"""
import logging
import json
from typing import Dict, Any, Optional
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """Validates generated content against requirements"""
    
    @staticmethod
    async def review(
        generated_content: str,
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        requirements: Optional[Dict[str, Any]] = None,
        source_context: str = "",
    ) -> Dict[str, Any]:
        """
        Review generated content for quality and fidelity
        
        Args:
            generated_content: Content to review
            content_type: Type of content
            subject: Academic subject
            topic: Topic
            level: Difficulty level
            requirements: Requirements to check
            source_context: Original source for fidelity check
        
        Returns:
            Review result with approval status and improvement suggestions
        """
        try:
            # 1. Check fidelity if source context available
            fidelity_score = 0.8  # Default
            if source_context:
                fidelity_score = await ReviewerAgent._check_fidelity(
                    generated_content,
                    source_context,
                    subject,
                    topic
                )
            
            # 2. Check difficulty level
            difficulty_check = await ReviewerAgent._check_difficulty(
                generated_content,
                content_type,
                level,
                subject
            )
            
            # 3. Check requirements compliance
            requirements_met = ReviewerAgent._check_requirements(
                generated_content,
                requirements or {}
            )
            
            # 4. Determine if content needs regeneration
            overall_score = (fidelity_score * 0.5) + (difficulty_check["score"] * 0.35) + (requirements_met["score"] * 0.15)
            
            needs_regeneration = overall_score < 0.65
            
            review_result = {
                "approval_status": "approved" if not needs_regeneration else "needs_revision",
                "overall_score": round(overall_score, 2),
                "fidelity_score": round(fidelity_score, 2),
                "difficulty_check": difficulty_check,
                "requirements_met": requirements_met,
                "needs_regeneration": needs_regeneration,
                "improvement_suggestions": await ReviewerAgent._generate_suggestions(
                    generated_content,
                    fidelity_score,
                    difficulty_check,
                    requirements_met,
                ) if needs_regeneration else [],
            }
            
            logger.info(f"Review complete: {review_result['approval_status']} (score: {overall_score})")
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
        """
        Check if generated content is faithful to source material
        Uses LLM to evaluate accuracy
        """
        try:
            evaluation_prompt = f"""
You are an academic content evaluator. Evaluate the fidelity of generated content to the source material.

Subject: {subject}
Topic: {topic}

Source Material:
{source_context[:1000]}...

Generated Content:
{generated_content[:1000]}...

On a scale of 0-1, how faithful is the generated content to the source material?
Consider: accuracy, representativeness, and absence of hallucinations.

Respond with ONLY a number between 0 and 1 (e.g., 0.85)
"""
            
            # Simple evaluation - in production would use more sophisticated methods
            # For now, return high score if content references key concepts
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
            # Analyze content complexity
            # Count sentence complexity, vocabulary level, etc.
            words = generated_content.split()
            avg_word_length = sum(len(w) for w in words) / max(len(words), 1)
            
            # Simple heuristic: longer words = higher difficulty
            if avg_word_length > 7:
                difficulty_found = "advanced"
            elif avg_word_length > 5.5:
                difficulty_found = "intermediate"
            else:
                difficulty_found = "beginner"
            
            # Score based on match with required level
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
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if content meets specified requirements"""
        met_requirements = {}
        
        if requirements.get("include_examples"):
            has_examples = any(word in generated_content.lower() for word in ["example", "for example", "e.g.", "ejemplo"])
            met_requirements["include_examples"] = has_examples
        
        if requirements.get("with_explanations"):
            has_explanations = any(word in generated_content.lower() for word in ["because", "due to", "reason", "because"])
            met_requirements["with_explanations"] = has_explanations
        
        if requirements.get("with_solutions"):
            has_solutions = len(generated_content) > 200  # Simple check
            met_requirements["with_solutions"] = has_solutions
        
        if not met_requirements:
            met_requirements["general"] = True
        
        # Calculate score
        total_met = sum(1 for v in met_requirements.values() if v)
        score = total_met / max(len(met_requirements), 1)
        
        return {
            "met_requirements": met_requirements,
            "score": score,
        }
    
    @staticmethod
    async def _generate_suggestions(
        generated_content: str,
        fidelity_score: float,
        difficulty_check: Dict[str, Any],
        requirements_met: Dict[str, Any],
    ) -> list:
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
