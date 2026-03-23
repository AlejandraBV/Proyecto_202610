"""
Content Generator Agent - Generates academic content based on context
Uses LLM to create exams, guides, questions, etc.
"""
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class GeneratorAgent:
    """Generates academic content using LLM"""
    
    @staticmethod
    async def generate(
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        user_prompt: str,
        retrieved_context: str = "",
        feedback_examples: Optional[list] = None,
        requirements: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate academic content
        
        Args:
            content_type: Type of content to generate
            subject: Academic subject
            topic: Specific topic
            level: Difficulty level
            user_prompt: User's request
            retrieved_context: Context retrieved from vector DB (RAG)
            feedback_examples: Previous feedback for few-shot learning
            requirements: Extracted requirements from prompt
        
        Returns:
            Generated content
        """
        try:
            # Build enhanced prompt with RAG context + feedback examples
            prompt = GeneratorAgent._build_enhanced_prompt(
                content_type=content_type,
                subject=subject,
                topic=topic,
                level=level,
                user_prompt=user_prompt,
                retrieved_context=retrieved_context,
                feedback_examples=feedback_examples,
                requirements=requirements,
            )
            
            # Generate using LLM
            generated_content = await LLMService.generate_content(
                content_type=content_type,
                subject=subject,
                topic=topic,
                level=level,
                additional_context=prompt,
                previous_feedback=None,
            )
            
            logger.info(f"Generated {content_type} content for {subject}/{topic}")
            return generated_content
            
        except Exception as e:
            logger.error(f"Error in generator agent: {e}")
            raise
    
    @staticmethod
    async def generate_stream(
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        user_prompt: str,
        retrieved_context: str = "",
        feedback_examples: Optional[list] = None,
        requirements: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate content with streaming (for real-time display)
        """
        try:
            prompt = GeneratorAgent._build_enhanced_prompt(
                content_type=content_type,
                subject=subject,
                topic=topic,
                level=level,
                user_prompt=user_prompt,
                retrieved_context=retrieved_context,
                feedback_examples=feedback_examples,
                requirements=requirements,
            )
            
            async for chunk in LLMService.generate_content_stream(
                content_type=content_type,
                subject=subject,
                topic=topic,
                level=level,
                additional_context=prompt,
                previous_feedback=None,
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in generator stream: {e}")
            raise
    
    @staticmethod
    def _build_enhanced_prompt(
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        user_prompt: str,
        retrieved_context: str = "",
        feedback_examples: Optional[list] = None,
        requirements: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build enhanced prompt with RAG context and few-shot examples"""
        
        content_instructions = {
            "exam": "Generate a comprehensive exam with multiple choice, short answer, and essay questions.",
            "slideshow": "Generate presentation slides content with key points, examples, and visual descriptions.",
            "guide": "Generate a detailed study or teaching guide with structured sections and explanations.",
            "question": "Generate thought-provoking, well-crafted academic questions.",
            "text": "Generate well-structured, comprehensive academic text content.",
        }
        
        instruction = content_instructions.get(content_type, "Generate academic content")
        
        prompt = f"""You are an expert academic content generator specializing in {subject}.

# Task
Create high-quality {content_type} content for the following:
- Subject: {subject}
- Topic: {topic}
- Level: {level}
- User Request: {user_prompt}

# Instructions
{instruction}

"""
        
        # Add requirements
        if requirements:
            if requirements.get("include_examples"):
                prompt += "- Include concrete, relevant examples\n"
            if requirements.get("with_explanations"):
                prompt += "- Provide clear explanations for concepts\n"
            if requirements.get("with_solutions"):
                prompt += "- Include solutions or answer keys\n"
            if requirements.get("include_references"):
                prompt += "- Include references to sources\n"
            prompt += "\n"
        
        # Add RAG context if available
        if retrieved_context:
            prompt += f"""# Reference Material Context
Use the following reference material to ensure accuracy and consistency:

{retrieved_context}

"""
        
        # Add few-shot examples from feedback
        if feedback_examples:
            prompt += "# Examples of Approved Content\nLearn from these approved examples:\n\n"
            for example in feedback_examples[:3]:  # Max 3 examples
                prompt += f"Example:\n{example.get('content', '')}\n\n"
        
        prompt += "\nGenerate the content now, making it engaging, accurate, and appropriate for the educational level."
        
        return prompt
