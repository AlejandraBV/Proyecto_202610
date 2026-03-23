"""
Content Orchestrator - LangGraph-based workflow orchestration
Implements RAG pipeline with agent-based generation, review, and feedback loops
"""
import logging
from typing import Dict, Any, List, Optional
from app.agents.analyzer_agent import AnalyzerAgent
from app.agents.generator_agent import GeneratorAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.feedback_agent import FeedbackAgent
from app.services.vector_service import VectorDatabaseService
from app.services.document_ingestion_service import DocumentIngestor, SemanticChunker

logger = logging.getLogger(__name__)


class ContentOrchestrator:
    """
    Orchestrates the RAG + Agent-based content generation workflow
    
    Workflow:
    1. Analyzer: Analyzes prompt and retrieves context from vector DB
    2. Generator: Generates content based on analysis
    3. Reviewer: Validates content for difficulty, fidelity, requirements
    4. Loop: If review fails, go back to Generator with improvement instructions
    5. Feedback: Capture teacher feedback and update learning examples
    """
    
    MAX_GENERATION_ATTEMPTS = 3  # Max times to regenerate if reviewer fails
    
    @staticmethod
    async def generate_with_rag_and_agents(
        conversation_id: str,
        user_prompt: str,
        subject: str,
        topic: str,
        level: str,
        user_id: str = None,
        document_context: Optional[str] = None,
        previous_feedback: Optional[list] = None,
        db: Any = None,
    ) -> Dict[str, Any]:
        """
        Complete RAG + Agent pipeline for content generation
        
        Steps:
        1. Analyze user prompt → determine content type, difficulty, retrieve context
        2. Generate content → use LLM with RAG context + few-shot examples
        3. Review content → validate fidelity, difficulty, requirements
        4. Loop if needed → regenerate with improvement suggestions
        5. Return final content with metadata
        
        Args:
            conversation_id: Conversation ID
            user_prompt: User's request
            subject: Academic subject
            topic: Academic topic
            level: Difficulty level
            user_id: User ID (for retrieving learning examples)
            document_context: Document uploaded by teacher
            previous_feedback: Previous iterations' feedback
            db: Database session
        
        Returns:
            Generated content with generation metadata
        """
        try:
            logger.info(f"Starting generation pipeline for {subject}/{topic}")
            
            # STEP 1: Analyze
            # ================
            analysis = await AnalyzerAgent.analyze(
                user_prompt=user_prompt,
                subject=subject,
                topic=topic,
                document_context=document_context,
                user_level=level,
            )
            
            content_type = analysis["content_type"]
            inferred_difficulty = analysis["difficulty_level"]
            retrieved_context = analysis["retrieved_context"]
            requirements = analysis["requirements"]
            
            # Get learning examples for few-shot prompting
            feedback_examples = []
            if user_id and db:
                feedback_examples = await FeedbackAgent.get_learning_examples(
                    user_id=user_id,
                    content_type=content_type,
                    subject=subject,
                    db=db,
                    limit=3,
                )
            
            logger.info(f"Analysis: {content_type}, difficulty: {inferred_difficulty}, context chunks: {len(retrieved_context)}")
            
            # STEP 2-4: Generate with review loop
            # ====================================
            generated_content = None
            review_result = None
            attempt = 0
            improvement_instructions = ""
            
            while attempt < ContentOrchestrator.MAX_GENERATION_ATTEMPTS:
                attempt += 1
                logger.info(f"Generation attempt {attempt}/{ContentOrchestrator.MAX_GENERATION_ATTEMPTS}")
                
                # Generate content
                generated_content = await GeneratorAgent.generate(
                    content_type=content_type,
                    subject=subject,
                    topic=topic,
                    level=inferred_difficulty,
                    user_prompt=user_prompt + improvement_instructions,
                    retrieved_context=retrieved_context,
                    feedback_examples=feedback_examples,
                    requirements=requirements,
                )
                
                # Review generated content
                review_result = await ReviewerAgent.review(
                    generated_content=generated_content,
                    content_type=content_type,
                    subject=subject,
                    topic=topic,
                    level=inferred_difficulty,
                    requirements=requirements,
                    source_context=document_context or retrieved_context,
                )
                
                logger.info(f"Review score: {review_result['overall_score']}, status: {review_result['approval_status']}")
                
                # Check if needs regeneration
                if not review_result["needs_regeneration"]:
                    logger.info("Content approved by reviewer")
                    break
                else:
                    # Build instructions for next attempt
                    improvement_instructions = "\n\nImprovement feedback: " + "\n".join(
                        review_result.get("improvement_suggestions", [])
                    )
                    logger.info(f"Content needs revision. Suggestions: {improvement_instructions}")
            
            # STEP 5: Prepare result
            # =====================
            result = {
                "conversation_id": conversation_id,
                "content": generated_content,
                "content_type": content_type,
                "subject": subject,
                "topic": topic,
                "level": inferred_difficulty,
                "status": "generated",
                "version": len(previous_feedback) + 1 if previous_feedback else 1,
                "analysis": analysis,
                "review": review_result,
                "generation_attempts": attempt,
                "analysis_confidence": analysis.get("analysis_confidence", 0.85),
                "review_score": review_result.get("overall_score", 0.75) if review_result else 0.75,
            }
            
            logger.info(f"Generation complete. Version {result['version']}, Score: {result['review_score']}")
            return result
            
        except Exception as e:
            logger.error(f"Error in content generation pipeline: {e}")
            raise
    
    @staticmethod
    async def process_teacher_feedback(
        content_id: str,
        feedback_text: str,
        status: str,
        editor_name: str,
        db: Any = None,
    ) -> Dict[str, Any]:
        """
        Process feedback from teacher in human-in-the-loop workflow
        
        Args:
            content_id: Generated content ID
            feedback_text: Teacher's feedback
            status: "approved", "needs_revision", "rejected"
            editor_name: Teacher's name
            db: Database session
        
        Returns:
            Feedback processing result with next actions
        """
        try:
            logger.info(f"Processing feedback for content {content_id}: {status}")
            
            # Process feedback
            feedback_result = await FeedbackAgent.process_feedback(
                content_id=content_id,
                feedback_text=feedback_text,
                status=status,
                editor_name=editor_name,
                db=db,
            )
            
            logger.info(f"Feedback recorded. Next action: {feedback_result['next_action']}")
            return feedback_result
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            raise
    
    @staticmethod
    async def ingest_teacher_document(
        document_id: str,
        file_path: str,
        file_type: str,
        subject: str,
        topic: str,
        user_id: str,
        conversation_id: str = None,
    ) -> Dict[str, Any]:
        """
        Ingest teacher's document for RAG pipeline
        
        Args:
            document_id: Unique document ID
            file_path: Path to file
            file_type: Type of file (pdf, docx, txt, url)
            subject: Academic subject
            topic: Academic topic
            user_id: Teacher's user ID
            conversation_id: Associated conversation (optional)
        
        Returns:
            Ingestion result with indexed chunks
        """
        try:
            logger.info(f"Starting document ingestion: {file_path}")
            
            # 1. Parse document
            raw_content = await DocumentIngestor.parse_file(file_path, file_type)
            logger.info(f"Parsed {len(raw_content)} characters")
            
            # 2. Chunk semantically
            chunked = SemanticChunker.chunk_with_metadata(
                text=raw_content,
                source=f"teacher_{user_id}",
                document_id=document_id,
            )
            logger.info(f"Created {len(chunked)} semantic chunks")
            
            # 3. Index in vector DB
            ingestion_result = await VectorDatabaseService.ingest_document(
                document_id=document_id,
                content=raw_content,
                document_source="teacher_upload",
                subject=subject,
                topic=topic,
            )
            
            logger.info(f"Ingestion complete: {ingestion_result['chunks_count']} chunks indexed")
            
            return {
                "document_id": document_id,
                "file_type": file_type,
                "chunks_created": len(chunked),
                "chunk_ids": ingestion_result["chunk_ids"],
                "status": "success",
            }
            
        except Exception as e:
            logger.error(f"Error ingesting document: {e}")
            raise
    
    @staticmethod
    async def get_conversation_state(
        conversation_id: str,
        db: Any = None,
    ) -> Dict[str, Any]:
        """
        Get complete state of a conversation including:
        - All generated content versions
        - Feedback history
        - Documents used
        """
        return {
            "conversation_id": conversation_id,
            "state": "active",
            # This would be expanded with DB queries
        }

