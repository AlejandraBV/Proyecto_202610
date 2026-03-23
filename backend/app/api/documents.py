"""
Document management and RAG pipeline endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
import os
import tempfile
from typing import Optional
from app.core.database import get_db
from app.core.security import decode_token
from app.schemas import DocumentUpload, DocumentResponse, DocumentAnalysis
from app.models.models import Document, Chunk, User
from app.orchestration.content_orchestrator import ContentOrchestrator
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def get_current_user_id(token: Optional[str]) -> str:
    """Extract user ID from token"""
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    token_str = token.replace("Bearer ", "")
    payload = decode_token(token_str)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return payload.get("sub")


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    subject: str = None,
    topic: str = None,
    conversation_id: str = None,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document for RAG ingestion
    
    Supports: PDF, DOCX, TXT
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization")
        
        user_id = get_current_user_id(authorization)
        
        # Validate file type
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {settings.ALLOWED_FILE_TYPES}"
            )
        
        # Validate file size
        content = await file.read()
        if len(content) > settings.MAX_DOCUMENT_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.MAX_DOCUMENT_SIZE / 1024 / 1024:.0f}MB"
            )
        
        # Save file temporarily
        document_id = str(uuid.uuid4())
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Ingest document through orchestrator
            ingestion_result = await ContentOrchestrator.ingest_teacher_document(
                document_id=document_id,
                file_path=tmp_path,
                file_type=file_ext,
                subject=subject or "General",
                topic=topic or "Unspecified",
                user_id=user_id,
                conversation_id=conversation_id,
            )
            
            # Save document metadata to DB
            document = Document(
                id=document_id,
                user_id=user_id,
                conversation_id=conversation_id,
                filename=file.filename,
                file_type=file_ext,
                original_content=content.decode('utf-8', errors='ignore')[:10000],  # Store preview
                chunks_count=ingestion_result.get("chunks_created", 0),
                vector_index_ids=str(ingestion_result.get("chunk_ids", [])),
            )
            
            db.add(document)
            await db.commit()
            await db.refresh(document)
            
            logger.info(f"Document uploaded: {file.filename} ({document_id})")
            
            return DocumentResponse.from_orm(document)
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-text")
async def ingest_text_content(
    content: str,
    subject: str,
    topic: str = None,
    conversation_id: str = None,
    authorization: str = None,
    db: AsyncSession = Depends(get_db),
) -> DocumentAnalysis:
    """
    Ingest raw text content directly (without file upload)
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization")
        
        user_id = get_current_user_id(authorization)
        
        document_id = str(uuid.uuid4())
        
        # Ingest through orchestrator
        ingestion_result = await ContentOrchestrator.ingest_teacher_document(
            document_id=document_id,
            file_path="",
            file_type="txt",
            subject=subject,
            topic=topic or "Unspecified",
            user_id=user_id,
            conversation_id=conversation_id,
        )
        
        # Save to DB
        document = Document(
            id=document_id,
            user_id=user_id,
            conversation_id=conversation_id,
            filename=f"text_input_{document_id[:8]}.txt",
            file_type="txt",
            original_content=content[:10000],
            chunks_count=ingestion_result.get("chunks_created", 0),
            vector_index_ids=str(ingestion_result.get("chunk_ids", [])),
        )
        
        db.add(document)
        await db.commit()
        
        logger.info(f"Text content ingested: {document_id}")
        
        return DocumentAnalysis(
            document_id=document_id,
            chunks_created=ingestion_result.get("chunks_created", 0),
            chunk_ids=ingestion_result.get("chunk_ids", []),
            subject=subject,
            topic=topic,
            status="success",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    conversation_id: str = None,
    authorization: str = None,
    db: AsyncSession = Depends(get_db),
):
    """List documents uploaded by user"""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization")
        
        user_id = get_current_user_id(authorization)
        
        query = select(Document).filter(Document.user_id == user_id)
        
        if conversation_id:
            query = query.filter(Document.conversation_id == conversation_id)
        
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return documents
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    authorization: str = None,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document"""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization")
        
        user_id = get_current_user_id(authorization)
        
        # Verify ownership
        result = await db.execute(
            select(Document).filter(
                Document.id == document_id,
                Document.user_id == user_id
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        await db.delete(document)
        await db.commit()
        
        logger.info(f"Document deleted: {document_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific document by ID"""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization")

        user_id = get_current_user_id(authorization)

        result = await db.execute(
            select(Document).filter(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve the individual text chunks for a document.

    Useful for debugging the RAG pipeline: inspect how the document was
    chunked and what text each chunk contains.
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization")

        user_id = get_current_user_id(authorization)

        # Verify ownership
        doc_result = await db.execute(
            select(Document).filter(
                Document.id == document_id,
                Document.user_id == user_id,
            )
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Fetch stored chunks
        chunk_result = await db.execute(
            select(Chunk)
            .filter(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        chunks = chunk_result.scalars().all()

        return {
            "document_id": document_id,
            "filename": document.filename,
            "total_chunks": len(chunks),
            "chunks": [
                {
                    "id": c.id,
                    "chunk_index": c.chunk_index,
                    "text": c.text,
                    "chunk_size": c.chunk_size,
                    "overlap_info": c.overlap_info,
                    "vector_id": c.vector_id,
                }
                for c in chunks
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chunks for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/semantic")
async def semantic_search(
    request: dict,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Perform semantic search over indexed documents"""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization")

        from app.services.vector_service import VectorDatabaseService

        query = request.get("query", "")
        subject = request.get("subject")
        topic = request.get("topic")
        limit = request.get("limit", 5)

        results = await VectorDatabaseService.query(
            query_text=query,
            n_results=limit,
            where_filter={"subject": subject} if subject else None,
        )

        chunks = []
        for idx, (doc, meta) in enumerate(
            zip(
                results.get("results", []),
                results.get("metadatas", [{}] * limit),
            )
        ):
            chunks.append({
                "chunkIndex": idx,
                "text": doc.get("content", ""),
                "chunkSize": len(doc.get("content", "")),
                "similarityScore": doc.get("relevance_score", 0.0),
                "metadata": meta,
            })

        return {
            "chunks": chunks,
            "totalFound": len(chunks),
            "query": query,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during semantic search: {e}")
        raise HTTPException(status_code=500, detail=str(e))
