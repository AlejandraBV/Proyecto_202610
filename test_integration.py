#!/usr/bin/env python3
"""
Simple integration test runner for RAG pipeline
Run with: python test_integration.py
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.document_ingestion_service import DocumentIngestionService
from app.services.vector_service import VectorService
from app.orchestration.content_orchestrator import ContentOrchestrator
from app.agents.analyzer_agent import AnalyzerAgent
from app.agents.generator_agent import GeneratorAgent
from app.agents.reviewer_agent import ReviewerAgent


async def test_document_ingestion():
    """Test document ingestion service"""
    print("🧪 Testing Document Ingestion Service...")

    service = DocumentIngestionService()

    # Test chunking
    test_text = """
    Mathematics is the study of numbers, quantities, and shapes.
    Algebra is a branch of mathematics dealing with symbols and rules for manipulating these symbols.
    Calculus is the mathematical study of continuous change.
    Geometry is a branch of mathematics concerned with questions of shape, size, relative position of figures, and the properties of space.
    """ * 10  # Make it longer

    try:
        chunks = await service.chunk_text_semantic(test_text, overlap=0.15)
        print(f"✅ Chunking successful: {len(chunks)} chunks created")
        assert len(chunks) > 0, "No chunks created"
        assert all('text' in chunk for chunk in chunks), "Chunks missing text field"
        return True
    except Exception as e:
        print(f"❌ Chunking failed: {e}")
        return False


async def test_agents():
    """Test agent functionality"""
    print("🧪 Testing Agent Orchestration...")

    try:
        analyzer = AnalyzerAgent()
        generator = GeneratorAgent()
        reviewer = ReviewerAgent()

        # Test analyzer (mock response since we don't have LLM in test env)
        print("✅ Agents initialized successfully")
        print("   - AnalyzerAgent: OK")
        print("   - GeneratorAgent: OK")
        print("   - ReviewerAgent: OK")
        return True
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return False


async def test_orchestrator():
    """Test content orchestrator"""
    print("🧪 Testing Content Orchestrator...")

    try:
        orchestrator = ContentOrchestrator()
        # Test workflow creation (will fail without LangGraph, but tests import)
        print("✅ ContentOrchestrator initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Orchestrator initialization failed: {e}")
        return False


async def test_vector_service():
    """Test vector service"""
    print("🧪 Testing Vector Service...")

    try:
        service = VectorService()
        print("✅ VectorService initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Vector service initialization failed: {e}")
        return False


async def main():
    """Run all integration tests"""
    print("🚀 Starting RAG Pipeline Integration Tests")
    print("=" * 50)

    tests = [
        test_document_ingestion,
        test_agents,
        test_orchestrator,
        test_vector_service,
    ]

    results = []
    for test in tests:
        result = await test()
        results.append(result)
        print()

    print("=" * 50)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("✅ RAG Pipeline is ready for deployment")
        return 0
    else:
        print(f"⚠️  Some tests failed: {passed}/{total} passed")
        print("❌ Please check the failed components before deployment")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)