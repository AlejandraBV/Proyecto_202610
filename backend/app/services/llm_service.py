"""
LLM Service for handling Gemini and GPT-4o interactions
"""
import json
from typing import Optional, AsyncGenerator
from app.core.config import settings


class LLMService:
    """Service for interacting with LLM providers"""
    
    @staticmethod
    async def generate_content(
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        additional_context: Optional[str] = None,
        previous_feedback: Optional[str] = None,
    ) -> str:
        """Generate academic content using configured LLM"""
        
        prompt = LLMService._build_prompt(
            content_type=content_type,
            subject=subject,
            topic=topic,
            level=level,
            additional_context=additional_context,
            previous_feedback=previous_feedback,
        )
        
        if settings.LLM_PROVIDER == "gemini":
            return await LLMService._generate_with_gemini(prompt)
        elif settings.LLM_PROVIDER == "openai":
            return await LLMService._generate_with_openai(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")
    
    @staticmethod
    async def generate_content_stream(
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        additional_context: Optional[str] = None,
        previous_feedback: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate content with streaming"""
        
        prompt = LLMService._build_prompt(
            content_type=content_type,
            subject=subject,
            topic=topic,
            level=level,
            additional_context=additional_context,
            previous_feedback=previous_feedback,
        )
        
        if settings.LLM_PROVIDER == "gemini":
            async for chunk in LLMService._generate_with_gemini_stream(prompt):
                yield chunk
        elif settings.LLM_PROVIDER == "openai":
            async for chunk in LLMService._generate_with_openai_stream(prompt):
                yield chunk
    
    @staticmethod
    def _build_prompt(
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        additional_context: Optional[str] = None,
        previous_feedback: Optional[str] = None,
    ) -> str:
        """Build prompt for LLM"""
        
        content_instructions = {
            "exam": "Generate a comprehensive exam with multiple choice, short answer, and essay questions.",
            "slideshow": "Generate presentation slides content with key points, examples, and visual descriptions.",
            "guide": "Generate a detailed study or teaching guide with structured sections and explanations.",
            "question": "Generate thought-provoking questions that test understanding and critical thinking.",
            "text": "Generate well-structured academic text content.",
        }
        
        instruction = content_instructions.get(content_type, "Generate academic content")
        
        prompt = f"""You are an expert academic content generator. Your task is to create high-quality educational content.

Subject: {subject}
Topic: {topic}
Educational Level: {level}
Content Type: {content_type}

Instructions: {instruction}

Return the content in a well-structured format. Make it engaging, accurate, and appropriate for the educational level.

"""
        
        if additional_context:
            prompt += f"Additional context or requirements:\n{additional_context}\n\n"
        
        if previous_feedback:
            prompt += f"Feedback from previous version (please incorporate):\n{previous_feedback}\n\n"
        
        prompt += "Generate the content now:"
        
        return prompt
    
    @staticmethod
    async def _generate_with_gemini(prompt: str) -> str:
        """Generate content using Gemini API"""
        import google.generativeai as genai
        
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        response = model.generate_content(prompt)
        return response.text
    
    @staticmethod
    async def _generate_with_gemini_stream(prompt: str) -> AsyncGenerator[str, None]:
        """Generate content with streaming from Gemini"""
        import google.generativeai as genai
        
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    
    @staticmethod
    async def _generate_with_openai(prompt: str) -> str:
        """Generate content using OpenAI API"""
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        
        return response.choices[0].message.content
    
    @staticmethod
    async def _generate_with_openai_stream(prompt: str) -> AsyncGenerator[str, None]:
        """Generate content with streaming from OpenAI"""
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
