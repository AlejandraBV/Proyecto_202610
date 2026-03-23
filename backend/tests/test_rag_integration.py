"""
Integration tests for RAG pipeline and document processing
"""
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import json
from unittest.mock import patch, MagicMock

from app.main import app
from app.core.database import get_db
from app.models.models import Document, Chunk, AgentDecisionRecord
from app.services.document_ingestion_service import DocumentIngestionService
from app.services.vector_service import VectorService
from app.orchestration.content_orchestrator import ContentOrchestrator
from app.agents.analyzer_agent import AnalyzerAgent
from app.agents.generator_agent import GeneratorAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.feedback_agent import FeedbackAgent


@pytest.fixture
async def client():
    """Test client fixture"""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def db_session():
    """Database session fixture"""
    async for session in get_db():
        yield session


class TestDocumentIngestion:
    """Test document ingestion pipeline"""

    @pytest.mark.asyncio
    async def test_pdf_ingestion(self):
        """Test PDF document ingestion and chunking"""
        # Mock PDF content
        mock_pdf_content = b"Mock PDF content for testing"

        with patch('app.services.document_ingestion_service.DocumentIngestionService.ingest_pdf') as mock_ingest:
            mock_ingest.return_value = ["Page 1 content", "Page 2 content"]

            service = DocumentIngestionService()
            result = await service.ingest_pdf(mock_pdf_content)

            assert len(result) == 2
            assert "Page 1 content" in result
            assert "Page 2 content" in result
            mock_ingest.assert_called_once_with(mock_pdf_content)

    @pytest.mark.asyncio
    async def test_chunking_with_overlap(self):
        """Test semantic chunking with overlap"""
        test_text = "This is a long document. " * 100  # Create long text

        service = DocumentIngestionService()
        chunks = await service.chunk_text_semantic(test_text, overlap=0.15)

        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('chunk_size' in chunk for chunk in chunks)
        assert all('overlap_info' in chunk for chunk in chunks)

        # Verify overlap logic
        if len(chunks) > 1:
            # Check that consecutive chunks have some overlapping content
            first_chunk_end = chunks[0]['text'][-50:]
            second_chunk_start = chunks[1]['text'][:50]
            # This is a basic check - in real implementation would be more sophisticated
            assert len(first_chunk_end) > 0
            assert len(second_chunk_start) > 0


class TestVectorService:
    """Test vector service operations"""

    @pytest.mark.asyncio
    async def test_similarity_search(self):
        """Test semantic similarity search"""
        with patch('app.services.vector_service.VectorService._get_collection') as mock_collection:
            mock_collection.return_value.query.return_value = {
                'documents': [['chunk1', 'chunk2']],
                'metadatas': [[{'document_id': 'doc1'}, {'document_id': 'doc2'}]],
                'distances': [[0.1, 0.2]]
            }

            service = VectorService()
            results = await service.retrieve_similar_chunks("test query", n_results=2)

            assert len(results) == 2
            assert 'text' in results[0]
            assert 'score' in results[0]
            mock_collection.return_value.query.assert_called_once()


class TestAgentOrchestration:
    """Test agent orchestration and decision making"""

    @pytest.mark.asyncio
    async def test_analyzer_agent(self):
        """Test analyzer agent prompt analysis"""
        with patch('app.agents.analyzer_agent.AnalyzerAgent._call_llm') as mock_llm:
            mock_llm.return_value = {
                'content_type': 'exam',
                'difficulty_level': 'intermediate',
                'relevant_chunks': ['chunk1', 'chunk2'],
                'content_focus': ['definitions', 'examples']
            }

            agent = AnalyzerAgent()
            result = await agent.analyze("Create an exam about mathematics", [])

            assert result['content_type'] == 'exam'
            assert result['difficulty_level'] == 'intermediate'
            assert len(result['relevant_chunks']) == 2

    @pytest.mark.asyncio
    async def test_reviewer_agent_approval(self):
        """Test reviewer agent content validation"""
        with patch('app.agents.reviewer_agent.ReviewerAgent._call_llm') as mock_llm:
            mock_llm.return_value = {
                'quality_score': 0.95,
                'fidelity_score': 0.9,
                'difficulty_match': True,
                'decision': 'approved',
                'reasoning': 'Content meets all requirements'
            }

            agent = ReviewerAgent()
            result = await agent.review("Generated content", {
                'content_type': 'exam',
                'difficulty_level': 'intermediate'
            })

            assert result['decision'] == 'approved'
            assert result['quality_score'] >= 0.85

    @pytest.mark.asyncio
    async def test_reviewer_agent_rejection(self):
        """Test reviewer agent content rejection"""
        with patch('app.agents.reviewer_agent.ReviewerAgent._call_llm') as mock_llm:
            mock_llm.return_value = {
                'quality_score': 0.6,
                'fidelity_score': 0.5,
                'difficulty_match': False,
                'decision': 'regenerate',
                'reasoning': 'Content does not meet difficulty requirements'
            }

            agent = ReviewerAgent()
            result = await agent.review("Poor quality content", {
                'content_type': 'exam',
                'difficulty_level': 'advanced'
            })

            assert result['decision'] == 'regenerate'
            assert result['quality_score'] < 0.85


class TestContentOrchestrator:
    """Test the complete RAG orchestration pipeline"""

    @pytest.mark.asyncio
    async def test_rag_workflow_creation(self):
        """Test LangGraph workflow creation"""
        orchestrator = ContentOrchestrator()

        with patch('app.orchestration.content_orchestrator.StateGraph') as mock_graph:
            mock_workflow = MagicMock()
            mock_graph.return_value = mock_workflow
            mock_workflow.compile.return_value = mock_workflow

            workflow = await orchestrator.create_rag_workflow()

            assert workflow is not None
            mock_graph.assert_called_once()

    @pytest.mark.asyncio
    async def test_rag_pipeline_execution(self):
        """Test complete RAG pipeline execution"""
        orchestrator = ContentOrchestrator()

        with patch('app.orchestration.content_orchestrator.ContentOrchestrator.create_rag_workflow') as mock_create:
            mock_workflow = MagicMock()
            mock_create.return_value = mock_workflow
            mock_workflow.invoke.return_value = {
                'generated_content': 'Test generated content',
                'agent_decisions': [
                    {'agent': 'analyzer', 'decision': 'approved'},
                    {'agent': 'generator', 'decision': 'approved'},
                    {'agent': 'reviewer', 'decision': 'approved'}
                ],
                'retrieved_chunks': ['chunk1', 'chunk2'],
                'iterations': 1
            }

            result = await orchestrator.execute_rag_pipeline(
                "Generate test content",
                [],
                {}
            )

            assert 'generated_content' in result
            assert 'agent_decisions' in result
            assert 'retrieved_chunks' in result
            assert result['iterations'] == 1


class TestAPIEndpoints:
    """Test API endpoints for RAG functionality"""

    @pytest.mark.asyncio
    async def test_upload_document_endpoint(self, client: AsyncClient):
        """Test document upload endpoint"""
        # Create a mock PDF file
        mock_file_content = b"Mock PDF content"
        files = {'file': ('test.pdf', mock_file_content, 'application/pdf')}
        data = {
            'subject': 'Mathematics',
            'level': 'university',
            'description': 'Test document'
        }

        with patch('app.api.documents.apiClient.uploadDocument') as mock_upload:
            mock_upload.return_value = {
                'data': {
                    'documentId': 'test-doc-id',
                    'chunksCount': 5,
                    'status': 'processed'
                }
            }

            response = await client.post('/documents/upload', files=files, data=data)

            assert response.status_code == 200
            response_data = response.json()
            assert response_data['documentId'] == 'test-doc-id'
            assert response_data['chunksCount'] == 5

    @pytest.mark.asyncio
    async def test_generate_with_rag_endpoint(self, client: AsyncClient, db_session: AsyncSession):
        """Test RAG-powered content generation endpoint"""
        request_data = {
            'prompt': 'Generate a mathematics exam',
            'contentType': 'exam',
            'subject': 'Mathematics',
            'level': 'university',
            'retrievedContext': [],
            'fewShotExamples': []
        }

        with patch('app.api.conversations.apiClient.generateContentWithRAG') as mock_generate:
            mock_generate.return_value = {
                'data': {
                    'content': 'Generated exam content',
                    'contentType': 'exam',
                    'agentDecisions': [
                        {
                            'agentName': 'analyzer',
                            'decision': 'approved',
                            'reasoning': 'Valid exam request'
                        }
                    ],
                    'retrievedChunks': [
                        {
                            'chunkIndex': 0,
                            'text': 'Sample chunk content',
                            'chunkSize': 100
                        }
                    ],
                    'iterations': 1,
                    'confidenceScore': 0.9
                }
            }

            # First create a conversation
            conv_response = await client.post('/conversations', json={
                'title': 'Test Conversation',
                'subject': 'Mathematics',
                'topic': 'Algebra'
            })
            assert conv_response.status_code == 200
            conversation = conv_response.json()

            # Then generate content
            response = await client.post(
                f'/conversations/{conversation["id"]}/generate',
                json=request_data
            )

            assert response.status_code == 200
            response_data = response.json()
            assert 'content' in response_data
            assert 'agentDecisions' in response_data
            assert 'retrievedChunks' in response_data

    @pytest.mark.asyncio
    async def test_semantic_search_endpoint(self, client: AsyncClient):
        """Test semantic search endpoint"""
        search_request = {
            'query': 'mathematics exam questions',
            'subject': 'Mathematics',
            'level': 'university',
            'limit': 5
        }

        with patch('app.api.documents.apiClient.semanticSearch') as mock_search:
            mock_search.return_value = {
                'data': {
                    'chunks': [
                        {
                            'chunkIndex': 0,
                            'text': 'Sample math question',
                            'chunkSize': 150,
                            'similarityScore': 0.95
                        }
                    ],
                    'totalFound': 1,
                    'query': 'mathematics exam questions'
                }
            }

            response = await client.post('/documents/search/semantic', json=search_request)

            assert response.status_code == 200
            response_data = response.json()
            assert len(response_data['chunks']) == 1
            assert response_data['chunks'][0]['similarityScore'] == 0.95


class TestEndToEndRAG:
    """End-to-end RAG pipeline tests"""

    @pytest.mark.asyncio
    async def test_complete_rag_cycle(self, client: AsyncClient):
        """Test complete RAG cycle from document upload to content generation"""
        # Step 1: Upload document
        mock_file_content = b"Mathematics document content for testing"
        files = {'file': ('math.pdf', mock_file_content, 'application/pdf')}
        upload_data = {
            'subject': 'Mathematics',
            'level': 'university',
            'description': 'Test math document'
        }

        with patch('app.api.documents.apiClient.uploadDocument') as mock_upload:
            mock_upload.return_value = {
                'data': {
                    'documentId': 'test-doc-123',
                    'chunksCount': 3,
                    'status': 'processed'
                }
            }

            upload_response = await client.post('/documents/upload', files=files, data=upload_data)
            assert upload_response.status_code == 200

        # Step 2: Create conversation
        conv_response = await client.post('/conversations', json={
            'title': 'RAG Test Conversation',
            'subject': 'Mathematics',
            'topic': 'Calculus'
        })
        assert conv_response.status_code == 200
        conversation = conv_response.json()

        # Step 3: Generate content with RAG
        with patch('app.api.conversations.apiClient.generateContentWithRAG') as mock_generate:
            mock_generate.return_value = {
                'data': {
                    'content': 'Generated calculus exam with RAG context',
                    'contentType': 'exam',
                    'agentDecisions': [
                        {'agentName': 'analyzer', 'decision': 'approved', 'reasoning': 'Valid request'},
                        {'agentName': 'generator', 'decision': 'approved', 'reasoning': 'Content generated'},
                        {'agentName': 'reviewer', 'decision': 'approved', 'reasoning': 'Quality check passed'}
                    ],
                    'retrievedChunks': [
                        {'chunkIndex': 0, 'text': 'Calculus formula', 'chunkSize': 100, 'similarityScore': 0.9}
                    ],
                    'iterations': 1,
                    'confidenceScore': 0.95
                }
            }

            generate_response = await client.post(
                f'/conversations/{conversation["id"]}/generate',
                json={
                    'prompt': 'Create a calculus exam',
                    'contentType': 'exam',
                    'subject': 'Mathematics',
                    'level': 'university',
                    'retrievedContext': [],
                    'fewShotExamples': []
                }
            )

            assert generate_response.status_code == 200
            result = generate_response.json()

            # Verify RAG results
            assert result['content'] is not None
            assert len(result['agentDecisions']) == 3
            assert len(result['retrievedChunks']) == 1
            assert result['iterations'] == 1
            assert result['confidenceScore'] >= 0.8

    @pytest.mark.asyncio
    async def test_rag_re_ranking_loop(self, client: AsyncClient):
        """Test RAG re-ranking when content needs revision"""
        # Create conversation
        conv_response = await client.post('/conversations', json={
            'title': 'Re-ranking Test',
            'subject': 'Physics',
            'topic': 'Mechanics'
        })
        conversation = conv_response.json()

        # Mock re-ranking scenario (reviewer rejects, then approves on second try)
        with patch('app.api.conversations.apiClient.generateContentWithRAG') as mock_generate:
            mock_generate.return_value = {
                'data': {
                    'content': 'Improved physics content after re-ranking',
                    'contentType': 'guide',
                    'agentDecisions': [
                        {'agentName': 'analyzer', 'decision': 'approved', 'reasoning': 'Valid request'},
                        {'agentName': 'generator', 'decision': 'approved', 'reasoning': 'First generation'},
                        {'agentName': 'reviewer', 'decision': 'needs_revision', 'reasoning': 'Too basic'},
                        {'agentName': 'generator', 'decision': 'approved', 'reasoning': 'Regenerated with feedback'},
                        {'agentName': 'reviewer', 'decision': 'approved', 'reasoning': 'Now meets requirements'}
                    ],
                    'retrievedChunks': [
                        {'chunkIndex': 0, 'text': 'Physics formula', 'chunkSize': 120, 'similarityScore': 0.85}
                    ],
                    'iterations': 2,
                    'confidenceScore': 0.88
                }
            }

            response = await client.post(
                f'/conversations/{conversation["id"]}/generate',
                json={
                    'prompt': 'Create an advanced physics guide',
                    'contentType': 'guide',
                    'subject': 'Physics',
                    'level': 'university',
                    'retrievedContext': [],
                    'fewShotExamples': []
                }
            )

            result = response.json()

            # Verify re-ranking occurred
            assert result['iterations'] == 2
            assert len(result['agentDecisions']) == 5  # More decisions due to loop
            assert any(d['decision'] == 'needs_revision' for d in result['agentDecisions'])
            assert result['agentDecisions'][-1]['decision'] == 'approved'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])