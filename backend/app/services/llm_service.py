"""
LLM Service - Google GenAI SDK with Vertex AI backend
Uses student Google Cloud credits via service account credentials.
"""
from typing import Optional, AsyncGenerator
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Gemini via Vertex AI (google-genai SDK)"""

    _client = None

    @classmethod
    def _get_client(cls):
        """Lazy-initialise the GenAI client (Vertex AI backend)."""
        if cls._client is None:
            from google import genai
            cls._client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION,
            )
            logger.info(
                "GenAI client initialised — project=%s location=%s",
                settings.GOOGLE_CLOUD_PROJECT,
                settings.GOOGLE_CLOUD_LOCATION,
            )
        return cls._client

    # ------------------------------------------------------------------
    # Public API (unchanged interface — only implementation changed)
    # ------------------------------------------------------------------

    @staticmethod
    async def generate_content(
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        additional_context: Optional[str] = None,
        previous_feedback: Optional[str] = None,
    ) -> str:
        """Generate academic content using Vertex AI Gemini."""
        prompt = LLMService._build_prompt(
            content_type=content_type,
            subject=subject,
            topic=topic,
            level=level,
            additional_context=additional_context,
            previous_feedback=previous_feedback,
        )
        return await LLMService._generate_with_gemini(prompt)

    @staticmethod
    async def generate_content_stream(
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        additional_context: Optional[str] = None,
        previous_feedback: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate content with streaming."""
        prompt = LLMService._build_prompt(
            content_type=content_type,
            subject=subject,
            topic=topic,
            level=level,
            additional_context=additional_context,
            previous_feedback=previous_feedback,
        )
        async for chunk in LLMService._generate_with_gemini_stream(prompt):
            yield chunk

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        content_type: str,
        subject: str,
        topic: str,
        level: str,
        additional_context: Optional[str] = None,
        previous_feedback: Optional[str] = None,
    ) -> str:
        content_instructions = {
            "exam": "Generate a comprehensive exam with multiple choice, short answer, and essay questions.",
            "slideshow": "Generate presentation slides with key points, examples, and visual descriptions.",
            "guide": "Generate a detailed study or teaching guide with structured sections and explanations.",
            "question": "Generate thought-provoking questions that test understanding and critical thinking.",
            "text": "Generate well-structured academic text content.",
        }
        instruction = content_instructions.get(content_type, "Generate academic content.")

        prompt = f"""You are an expert academic content generator. Create high-quality educational content.

Subject: {subject}
Topic: {topic}
Educational Level: {level}
Content Type: {content_type}

Instructions: {instruction}

Return well-structured content — engaging, accurate, and appropriate for the educational level.

"""
        if additional_context:
            prompt += f"Additional context / requirements:\n{additional_context}\n\n"
        if previous_feedback:
            prompt += f"Feedback from previous version (incorporate this):\n{previous_feedback}\n\n"

        prompt += "Generate the content now:"
        return prompt

    @staticmethod
    async def infer_subject(text_preview: str) -> str:
        """Infer the academic subject from a document text preview."""
        prompt = (
            "You are classifying an academic document. Based on the text excerpt below, "
            "identify the academic subject (e.g. Mathematics, Physics, History, Literature, "
            "Computer Science, Biology, Economics, Chemistry, Philosophy, etc.).\n\n"
            f"Text excerpt:\n{text_preview[:2000]}\n\n"
            "Respond with ONLY the subject name, nothing else. "
            "Examples: \"Mathematics\", \"History\", \"Computer Science\""
        )
        client = LLMService._get_client()
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )
        return response.text.strip()

    @staticmethod
    async def generate_with_prompt(prompt: str) -> str:
        """
        Generate content from a fully pre-built prompt string.
        Use this when the caller has already assembled the complete prompt
        (e.g. GeneratorAgent) to avoid double-wrapping with _build_prompt.
        """
        return await LLMService._generate_with_gemini(prompt)

    @staticmethod
    async def _generate_with_gemini(prompt: str) -> str:
        """Async content generation via Vertex AI Gemini."""
        client = LLMService._get_client()
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )
        return response.text

    @staticmethod
    async def _generate_with_gemini_stream(prompt: str) -> AsyncGenerator[str, None]:
        """
        Simulated streaming: generates the full response then emits it in
        small character chunks so the UI updates progressively.
        Vertex AI buffers the entire response before returning, so native
        streaming gives no UX benefit — this approach is more reliable.
        """
        import asyncio
        full_text = await LLMService._generate_with_gemini(prompt)
        CHUNK_SIZE = 25  # characters per chunk (~500 chars/s at 20ms delay)
        for i in range(0, len(full_text), CHUNK_SIZE):
            yield full_text[i:i + CHUNK_SIZE]
            await asyncio.sleep(0.02)
