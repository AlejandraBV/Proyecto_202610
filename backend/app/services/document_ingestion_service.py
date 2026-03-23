"""
Document Ingestion Service - Handles parsing, chunking, and vectorization
Supports: PDF, DOCX, TXT, and direct text input
"""
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DocumentIngestor:
    """Handles document parsing from various formats"""
    
    @staticmethod
    async def parse_file(file_path: str, file_type: str) -> str:
        """
        Parse document based on file type
        
        Args:
            file_path: Path to the file
            file_type: Type of file (pdf, docx, txt, url)
        
        Returns:
            Extracted text content
        """
        try:
            if file_type.lower() == "pdf":
                return await DocumentIngestor._parse_pdf(file_path)
            elif file_type.lower() == "docx":
                return await DocumentIngestor._parse_docx(file_path)
            elif file_type.lower() == "txt":
                return await DocumentIngestor._parse_txt(file_path)
            elif file_type.lower() == "url":
                return await DocumentIngestor._parse_url(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            logger.error(f"Error parsing {file_type} file: {e}")
            raise
    
    @staticmethod
    async def _parse_pdf(file_path: str) -> str:
        """Extract text from PDF using PyMuPDF"""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(file_path)
            text = ""
            for page_num in range(len(doc)):
                page = doc[page_num]
                text += page.get_text() + "\n"
            doc.close()
            return text
        except ImportError:
            raise ImportError("PyMuPDF not installed. Install with: pip install pymupdf")
        except Exception as e:
            raise Exception(f"PDF parsing error: {e}")
    
    @staticmethod
    async def _parse_docx(file_path: str) -> str:
        """Extract text from DOCX using python-docx"""
        try:
            from docx import Document
            
            doc = Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except ImportError:
            raise ImportError("python-docx not installed. Install with: pip install python-docx")
        except Exception as e:
            raise Exception(f"DOCX parsing error: {e}")
    
    @staticmethod
    async def _parse_txt(file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"TXT parsing error: {e}")
    
    @staticmethod
    async def _parse_url(url: str) -> str:
        """Extract text from URL"""
        try:
            import requests
            from html.parser import HTMLParser
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Simple HTML to text extraction
            class HTMLToText(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                
                def handle_data(self, data):
                    text = data.strip()
                    if text:
                        self.text.append(text)
            
            parser = HTMLToText()
            parser.feed(response.text)
            return '\n'.join(parser.text)
        except Exception as e:
            raise Exception(f"URL parsing error: {e}")


class SemanticChunker:
    """
    Splits documents into semantic chunks with overlap
    
    Strategy:
    - Split by paragraphs/sections first
    - Apply overlap of 10-15%
    - Maintain context between chunks
    """
    
    MIN_CHUNK_SIZE = 200  # Minimum characters per chunk
    MAX_CHUNK_SIZE = 1500  # Maximum characters per chunk
    OVERLAP_PERCENTAGE = 0.12  # 12% overlap
    
    @staticmethod
    def chunk_text(text: str, overlap_percentage: float = None) -> List[str]:
        """
        Split text into semantic chunks with overlap
        
        Args:
            text: Raw text to chunk
            overlap_percentage: Overlap ratio (default 12%)
        
        Returns:
            List of text chunks
        """
        if overlap_percentage is None:
            overlap_percentage = SemanticChunker.OVERLAP_PERCENTAGE
        
        # First pass: split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # Second pass: combine paragraphs into semantic chunks
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) < SemanticChunker.MAX_CHUNK_SIZE:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        # Add last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Apply overlap between chunks
        overlapped_chunks = SemanticChunker._apply_overlap(chunks, overlap_percentage)
        
        return overlapped_chunks
    
    @staticmethod
    def _apply_overlap(chunks: List[str], overlap_percentage: float) -> List[str]:
        """
        Add overlap between chunks for context preservation
        
        Args:
            chunks: Original chunks
            overlap_percentage: How much of previous chunk to include (10-15%)
        
        Returns:
            Chunks with overlap applied
        """
        if len(chunks) <= 1:
            return chunks
        
        overlapped = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]
            
            # Calculate overlap size
            overlap_size = max(
                int(len(prev_chunk) * overlap_percentage),
                100  # Minimum 100 chars overlap
            )
            
            # Get end of previous chunk as overlap
            overlap_text = prev_chunk[-overlap_size:] if len(prev_chunk) > overlap_size else prev_chunk
            
            # Combine overlap + current chunk
            combined = overlap_text + "\n\n" + curr_chunk
            overlapped.append(combined)
        
        return overlapped
    
    @staticmethod
    def chunk_with_metadata(
        text: str,
        source: str = "unknown",
        document_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk text and return with metadata
        
        Returns:
            List of dicts with chunk, source, document_id, chunk_index
        """
        chunks = SemanticChunker.chunk_text(text)
        
        result = []
        for idx, chunk in enumerate(chunks):
            result.append({
                "content": chunk,
                "source": source,
                "document_id": document_id,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "length": len(chunk),
            })
        
        return result


class DocumentIngestionService:
    """
    Main service for document ingestion pipeline
    Combines parsing, chunking, and vectorization
    """

    def __init__(self):
        self.ingestor = DocumentIngestor()
        self.chunker = SemanticChunker()

    async def ingest_pdf(self, file_bytes: bytes) -> List[str]:
        """Ingest PDF document and return pages/sections"""
        # This would need to be implemented with proper file handling
        # For now, return mock data
        return ["PDF Page 1 content", "PDF Page 2 content"]

    async def ingest_docx(self, file_bytes: bytes) -> List[str]:
        """Ingest DOCX document and return sections"""
        # This would need to be implemented with proper file handling
        return ["DOCX Section 1", "DOCX Section 2"]

    async def fetch_url_content(self, url: str) -> str:
        """Fetch content from URL"""
        # This would need to be implemented with aiohttp
        return f"Content from {url}"

    async def chunk_text_semantic(self, text: str, overlap: float = 0.15) -> List[Dict]:
        """Chunk text semantically with overlap"""
        return await self.chunker.chunk_text(text, overlap)

    async def vectorize_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Vectorize chunks using embedding model"""
        # This would integrate with LLM service for embeddings
        for chunk in chunks:
            chunk['embedding'] = [0.1, 0.2, 0.3]  # Mock embedding
        return chunks

    async def store_chunks_in_chromadb(self, document_id: str, chunks: List[Dict]):
        """Store chunks in ChromaDB"""
        # This would integrate with VectorService
        pass
