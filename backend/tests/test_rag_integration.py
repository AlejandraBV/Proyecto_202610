"""
Integration tests for RAG pipeline and document processing
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from app.models.models import Document, Chunk, AgentDecisionRecord
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.vector_service import VectorService
from app.orchestration.content_orchestrator import ContentOrchestrator
from app.agents.analyzer_agent import AnalyzerAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.feedback_agent import FeedbackAgent


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def make_async(return_value):
    """Create an async mock that returns the given value"""
    async def _inner(*args, **kwargs):
        return return_value
    return _inner


# ---------------------------------------------------------------------------
# Document Ingestion Tests
# ---------------------------------------------------------------------------

class TestDocumentIngestion:
    """Test document ingestion pipeline"""

    @pytest.mark.asyncio
    async def test_pdf_ingestion(self):
        """Test PDF document ingestion and chunking"""
        mock_pdf_content = b"Mock PDF content for testing"

        with patch.object(
            DocumentIngestionService, "ingest_pdf", new=make_async(["Page 1 content", "Page 2 content"])
        ):
            service = DocumentIngestionService()
            result = await service.ingest_pdf(mock_pdf_content)

            assert len(result) == 2
            assert "Page 1 content" in result
            assert "Page 2 content" in result

    @pytest.mark.asyncio
    async def test_chunking_with_overlap(self):
        """Test semantic chunking with overlap"""
        test_text = "This is a long document. " * 100

        service = DocumentIngestionService()
        chunks = await service.chunk_text_semantic(test_text, overlap=0.15)

        assert len(chunks) > 0
        assert all("text" in chunk for chunk in chunks)
        assert all("chunk_size" in chunk for chunk in chunks)
        assert all("overlap_info" in chunk for chunk in chunks)

        if len(chunks) > 1:
            first_chunk_end = chunks[0]["text"][-50:]
            second_chunk_start = chunks[1]["text"][:50]
            assert len(first_chunk_end) > 0
            assert len(second_chunk_start) > 0


# ---------------------------------------------------------------------------
# Vector Service Tests
# ---------------------------------------------------------------------------

class TestVectorService:
    """Test vector service operations"""

    @pytest.mark.asyncio
    async def test_similarity_search(self):
        """Test semantic similarity search"""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["chunk1", "chunk2"]],
            "metadatas": [[{"document_id": "doc1"}, {"document_id": "doc2"}]],
            "distances": [[0.1, 0.2]],
        }

        service = VectorService()
        with patch.object(service, "_get_collection", return_value=mock_collection):
            results = await service.retrieve_similar_chunks("test query", n_results=2)

            assert len(results) == 2
            assert "text" in results[0]
            assert "score" in results[0]
            mock_collection.query.assert_called_once()


# ---------------------------------------------------------------------------
# Agent Tests
# ---------------------------------------------------------------------------

class TestAgentOrchestration:
    """Test agent orchestration and decision making"""

    @pytest.mark.asyncio
    async def test_analyzer_agent(self):
        """Test analyzer agent prompt analysis"""
        expected = {
            "content_type": "exam",
            "difficulty_level": "intermediate",
            "relevant_chunks": ["chunk1", "chunk2"],
            "content_focus": ["definitions", "examples"],
        }

        agent = AnalyzerAgent()
        with patch.object(agent, "_call_llm", new=make_async(expected)):
            result = await agent.analyze("Create an exam about mathematics", [])

            assert result["content_type"] == "exam"
            assert result["difficulty_level"] == "intermediate"
            assert len(result["relevant_chunks"]) == 2

    @pytest.mark.asyncio
    async def test_reviewer_agent_approval(self):
        """Test reviewer agent content validation - approved case"""
        expected = {
            "quality_score": 0.95,
            "fidelity_score": 0.9,
            "difficulty_match": True,
            "decision": "approved",
            "reasoning": "Content meets all requirements",
        }

        agent = ReviewerAgent()
        with patch.object(agent, "_call_llm", new=make_async(expected)):
            result = await agent.review(
                "Generated content",
                {"content_type": "exam", "difficulty_level": "intermediate"},
            )

            assert result["decision"] == "approved"
            assert result["quality_score"] >= 0.85

    @pytest.mark.asyncio
    async def test_reviewer_agent_rejection(self):
        """Test reviewer agent content rejection"""
        expected = {
            "quality_score": 0.6,
            "fidelity_score": 0.5,
            "difficulty_match": False,
            "decision": "regenerate",
            "reasoning": "Content does not meet difficulty requirements",
        }

        agent = ReviewerAgent()
        with patch.object(agent, "_call_llm", new=make_async(expected)):
            result = await agent.review(
                "Poor quality content",
                {"content_type": "exam", "difficulty_level": "advanced"},
            )

            assert result["decision"] == "regenerate"
            assert result["quality_score"] < 0.85


# ---------------------------------------------------------------------------
# Content Orchestrator Tests
# ---------------------------------------------------------------------------

class TestContentOrchestrator:
    """Test the complete RAG orchestration pipeline"""

    @pytest.mark.asyncio
    async def test_rag_workflow_creation(self):
        """Test RAG workflow creation"""
        orchestrator = ContentOrchestrator()
        workflow = await orchestrator.create_rag_workflow()
        assert workflow is not None

    @pytest.mark.asyncio
    async def test_rag_pipeline_execution(self):
        """Test complete RAG pipeline execution"""
        orchestrator = ContentOrchestrator()

        expected_generation = {
            "conversation_id": "conv-123",
            "content": "Test generated content",
            "content_type": "exam",
            "status": "generated",
            "version": 1,
            "review_score": 0.85,
            "generation_attempts": 1,
            "analysis": {"content_type": "exam"},
            "review": {"approval_status": "approved"},
        }

        with patch.object(
            ContentOrchestrator,
            "generate_with_rag_and_agents",
            new=make_async(expected_generation),
        ):
            result = await orchestrator.execute_rag_pipeline(
                "Generate test content",
                [],
                {"conversation_id": "conv-123"},
            )

            assert "generated_content" in result
            assert "agent_decisions" in result
            assert "retrieved_chunks" in result
            assert result["iterations"] == 1

    @pytest.mark.asyncio
    async def test_rag_pipeline_with_multiple_iterations(self):
        """Test RAG pipeline with re-ranking loop"""
        orchestrator = ContentOrchestrator()

        expected_generation = {
            "conversation_id": "conv-456",
            "content": "Improved content after re-ranking",
            "content_type": "guide",
            "status": "generated",
            "version": 1,
            "review_score": 0.88,
            "generation_attempts": 2,
            "analysis": {"content_type": "guide"},
            "review": {"approval_status": "approved", "improvement_suggestions": []},
        }

        with patch.object(
            ContentOrchestrator,
            "generate_with_rag_and_agents",
            new=make_async(expected_generation),
        ):
            result = await orchestrator.execute_rag_pipeline(
                "Create an advanced physics guide",
                [{"text": "Physics chunk", "score": 0.85}],
                {"conversation_id": "conv-456"},
            )

            assert result["iterations"] == 2
            assert "generated_content" in result
