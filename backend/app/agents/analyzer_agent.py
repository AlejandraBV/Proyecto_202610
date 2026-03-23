"""
Analyzer Agent - Analyzes user prompt and documents
Determines content type, difficulty level, and retrieved context
"""
import logging
from typing import Dict, Any, Optional
from app.services.vector_service import VectorDatabaseService

logger = logging.getLogger(__name__)


class AnalyzerAgent:
    """Analyzes user input and prepares context for generation"""
    
    CONTENT_TYPES = ["exam", "slideshow", "guide", "question", "text"]
    DIFFICULTY_LEVELS = ["beginner", "intermediate", "advanced", "expert"]
    
    @staticmethod
    async def analyze(
        user_prompt: str,
        subject: str,
        topic: str,
        document_context: Optional[str] = None,
        user_level: str = "intermediate",
    ) -> Dict[str, Any]:
        """
        Analyze user prompt and return analysis
        
        Args:
            user_prompt: User's request
            subject: Academic subject
            topic: Topic/subtopic
            document_context: Optional document content for analysis
            user_level: Expected difficulty level
        
        Returns:
            Analysis dict with inferred content type, difficulty, and context
        """
        try:
            # 1. Infer content type from prompt
            inferred_type = AnalyzerAgent._infer_content_type(user_prompt)
            
            # 2. Infer difficulty level
            inferred_difficulty = AnalyzerAgent._infer_difficulty(
                user_prompt,
                user_level
            )
            
            # 3. Retrieve relevant context from vector DB
            rag_context = ""
            if document_context or user_prompt:
                rag_context = await VectorDatabaseService.get_context_for_query(
                    user_query=user_prompt or topic,
                    subject=subject,
                    topic=topic,
                    top_k=5
                )
            
            # 4. Extract any specific requirements from prompt
            requirements = AnalyzerAgent._extract_requirements(user_prompt)
            
            analysis = {
                "content_type": inferred_type,
                "difficulty_level": inferred_difficulty,
                "retrieved_context": rag_context,
                "requirements": requirements,
                "analysis_confidence": 0.85,
                "ready_for_generation": True,
            }
            
            logger.info(f"Analysis complete: {inferred_type} at {inferred_difficulty} level")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in analyzer agent: {e}")
            raise
    
    @staticmethod
    def _infer_content_type(prompt: str) -> str:
        """Infer content type from prompt keywords"""
        prompt_lower = prompt.lower()
        
        keywords_map = {
            "exam": ["exam", "test", "quiz", "questions", "assessment"],
            "slideshow": ["slides", "presentation", "powerpoint", "diapositivas"],
            "guide": ["guide", "tutorial", "how-to", "manual", "guía"],
            "question": ["create questions", "generate questions", "preguntas"],
            "text": ["text", "write", "content", "redactar"],
        }
        
        for content_type, keywords in keywords_map.items():
            if any(kw in prompt_lower for kw in keywords):
                return content_type
        
        return "text"  # Default
    
    @staticmethod
    def _infer_difficulty(prompt: str, user_level: str) -> str:
        """Infer difficulty level from prompt and user level"""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["difficult", "hard", "challenging", "advanced"]):
            return "advanced"
        elif any(word in prompt_lower for word in ["easy", "basic", "beginner", "simple"]):
            return "beginner"
        elif any(word in prompt_lower for word in ["intermediate", "medium"]):
            return "intermediate"
        
        return user_level or "intermediate"
    
    @staticmethod
    def _extract_requirements(prompt: str) -> Dict[str, Any]:
        """Extract specific requirements from prompt"""
        requirements = {
            "include_examples": "examples" in prompt.lower() or "ejemplos" in prompt.lower(),
            "include_references": "references" in prompt.lower() or "referencias" in prompt.lower(),
            "with_explanations": "explain" in prompt.lower() or "explicar" in prompt.lower(),
            "with_solutions": "solutions" in prompt.lower() or "soluciones" in prompt.lower(),
        }
        
        return requirements
