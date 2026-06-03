"""
Vector Database Service - ChromaDB wrapper for semantic search and RAG
"""
import chromadb
import json
import hashlib
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.services.document_ingestion_service import SemanticChunker
import logging

logger = logging.getLogger(__name__)


class VectorDatabaseService:
    """Service for ChromaDB operations"""
    
    _client = None
    _collection = None
    
    @classmethod
    def get_client(cls):
        """Get or create ChromaDB client"""
        if cls._client is None:
            cls._client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
        return cls._client
    
    @classmethod
    def get_collection(cls, name: str = "academic_content"):
        """Get or create collection"""
        client = cls.get_client()
        return client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
    
    @classmethod
    async def ingest_document(
        cls,
        document_id: str,
        content: str,
        document_source: str = "user_upload",
        subject: str = None,
        topic: str = None,
    ) -> Dict[str, Any]:
        """
        Ingest document: chunk, vectorize, and index in ChromaDB
        
        Args:
            document_id: Unique document identifier
            content: Raw document content
            document_source: Source of document
            subject: Academic subject
            topic: Academic topic
        
        Returns:
            Ingestion result with indexed IDs
        """
        try:
            # 1. Chunk the document semantically
            chunked_data = SemanticChunker.chunk_with_metadata(
                text=content,
                source=document_source,
                document_id=document_id
            )
            
            # 2. Prepare for indexing
            documents = [chunk["content"] for chunk in chunked_data]
            ids = [f"{document_id}_chunk_{idx}" for idx in range(len(documents))]
            
            # 3. Create metadata
            metadatas = []
            for chunk in chunked_data:
                metadata = {
                    "document_id": document_id,
                    "chunk_index": str(chunk["chunk_index"]),
                    "total_chunks": str(chunk["total_chunks"]),
                    "source": chunk["source"],
                }
                if subject:
                    metadata["subject"] = subject
                if topic:
                    metadata["topic"] = topic
                metadatas.append(metadata)
            
            # 4. Add to ChromaDB
            collection = cls.get_collection()
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            
            logger.info(f"Ingested document {document_id} with {len(documents)} chunks")
            
            return {
                "document_id": document_id,
                "chunks_count": len(documents),
                "chunk_ids": ids,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error ingesting document: {e}")
            raise
    
    @classmethod
    async def query(
        cls,
        query_text: str,
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query vector database for similar documents
        
        Args:
            query_text: Query string
            n_results: Number of results to return
            where_filter: Optional filter on metadata
        
        Returns:
            Query results with documents and metadata
        """
        try:
            collection = cls.get_collection()

            # ChromaDB raises when the collection is empty — check first
            if collection.count() == 0:
                logger.info("Vector collection is empty; returning no results")
                return {"query": query_text, "results": [], "count": 0}

            # Clamp n_results to actual collection size to avoid ChromaDB errors
            actual_count = collection.count()
            n_results = min(n_results, actual_count)

            # Execute query
            if where_filter:
                results = collection.query(
                    query_texts=[query_text],
                    n_results=n_results,
                    where=where_filter
                )
            else:
                results = collection.query(
                    query_texts=[query_text],
                    n_results=n_results,
                )

            # Format results
            return {
                "query": query_text,
                "results": [
                    {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None,
                    }
                    for i in range(len(results["ids"][0]))
                ] if results["ids"] and len(results["ids"]) > 0 else [],
                "count": len(results["ids"][0]) if results["ids"] and len(results["ids"]) > 0 else 0,
            }
        except Exception as e:
            logger.error(f"Error querying vector database: {e}")
            raise
    
    @classmethod
    async def add_documents(
        cls,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
    ):
        """Add documents to vector database (legacy)"""
        collection = cls.get_collection()
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
    
    @classmethod
    async def delete_documents(cls, ids: List[str]):
        """Delete documents from vector database"""
        collection = cls.get_collection()
        collection.delete(ids=ids)
    
    @classmethod
    async def get_context_for_query(
        cls,
        user_query: str,
        subject: str = None,
        topic: str = None,
        top_k: int = 5
    ) -> str:
        """
        Get relevant context from vector DB for a user query
        This is used to build prompts for the LLM
        
        Args:
            user_query: User's question/request
            subject: Filter by subject
            topic: Filter by topic
            top_k: Number of chunks to retrieve
        
        Returns:
            Concatenated context string
        """
        # Build filter if needed — ChromaDB requires $and for multiple conditions
        where_filter = None
        conditions = []
        if subject:
            conditions.append({"subject": {"$eq": subject}})
        if topic:
            conditions.append({"topic": {"$eq": topic}})
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}
        
        # Query for similar documents — gracefully degrade if collection is empty
        try:
            results = await cls.query(
                query_text=user_query,
                n_results=top_k,
                where_filter=where_filter
            )
            context = "\n\n---\n\n".join([r["content"] for r in results["results"]])
        except Exception as e:
            logger.warning(f"Vector DB query failed (no context will be used): {e}")
            context = ""

        return context


class VectorService:
    """
    Instance-based wrapper for VectorDatabaseService.
    Provides instance methods for easier testing and dependency injection.
    """

    @staticmethod
    def _extract_chunk_text(chunk) -> str:
        """Normalize a chunk to its text content, accepting both str and dict."""
        if isinstance(chunk, dict):
            return chunk.get("text", "")
        return str(chunk)

    def _get_collection(self, name: str = "academic_content"):
        """Get ChromaDB collection"""
        return VectorDatabaseService.get_collection(name)

    async def retrieve_similar_chunks(
        self,
        query: str,
        n_results: int = 5,
        subject: str = None,
        topic: str = None,
    ) -> list:
        """
        Retrieve similar chunks from ChromaDB.

        Args:
            query: Query string for similarity search
            n_results: Number of results to return
            subject: Optional subject filter
            topic: Optional topic filter

        Returns:
            List of dicts with 'text' and 'score' keys
        """
        # ChromaDB requires $and for multiple conditions
        conditions = []
        if subject:
            conditions.append({"subject": {"$eq": subject}})
        if topic:
            conditions.append({"topic": {"$eq": topic}})
        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}
        else:
            where_filter = None

        collection = self._get_collection()
        query_result = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        results = []
        documents = query_result.get("documents", [[]])[0]
        distances = query_result.get("distances", [[]])[0]
        metadatas = query_result.get("metadatas", [[]])[0]

        for doc, dist, meta in zip(documents, distances, metadatas):
            results.append({
                "text": doc,
                "score": 1.0 - dist if dist is not None else 0.5,
                "metadata": meta,
            })

        return results

    async def add_chunks(
        self,
        document_id: str,
        chunks: list,
        subject: str = None,
        topic: str = None,
    ) -> dict:
        """Add document chunks to ChromaDB"""
        return await VectorDatabaseService.ingest_document(
            document_id=document_id,
            content="\n\n".join(VectorService._extract_chunk_text(c) for c in chunks),
            subject=subject,
            topic=topic,
        )
