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
        """
        Extract visible text from a URL.

        Strategy
        ────────
        1. Regex-remove entire block content of invisible elements
           (script, style, noscript, svg, math, head).
           • Using (?=[ \\t\\n\\r\\f\\v>]) after the tag name avoids matching
             e.g. <header> when looking for <head>.
           • re.DOTALL handles multi-line scripts / style blocks.
        2. Strip all remaining HTML tags (< ... >).
        3. Decode HTML entities (&amp; → &, &eacute; → é, &#160; → nbsp, …).
        4. Collapse whitespace, discard trivially short lines.
        5. Deduplicate consecutive identical lines (nav menus repeat).

        This avoids Python HTMLParser's depth-tracking, which breaks on pages
        that use IE conditional comments (<!--[if IE 8]>…<![endif]-->) because
        those comments confuse the tag-depth counter and can leave _skip_depth
        stuck at ≥ 1 for the entire body.
        """
        try:
            import requests
            import html as html_module

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            }
            response = requests.get(url, timeout=15, headers=headers)
            response.raise_for_status()

            # ── Encoding fix ───────────────────────────────────────────────
            # Many servers (especially Spanish/Latin-American news sites) return
            # UTF-8 HTML but either omit or mis-declare the charset as
            # ISO-8859-1 / Latin-1.  requests then decodes the bytes as
            # Latin-1, turning é → Ã© and ó → Ã³ (the classic "mojibake").
            # Strategy: always try UTF-8 first; fall back to the server-declared
            # encoding only if the bytes are not valid UTF-8.
            try:
                html_content = response.content.decode("utf-8")
            except (UnicodeDecodeError, LookupError):
                # Genuine non-UTF-8 page; respect what the server declared
                enc = response.encoding or "utf-8"
                html_content = response.content.decode(enc, errors="replace")

            # ── Step 1: remove entire block content for invisible elements ──
            # (?=[\s>]) after the tag name ensures <head> matches but <header>
            # does not.  </\1\s*> uses a back-reference so only the correct
            # closing tag terminates the block.
            _BLOCK_RE = re.compile(
                r"<(script|style|noscript|svg|math|head)(?=[\s>])[^>]*>"
                r".*?</\1\s*>",
                re.DOTALL | re.IGNORECASE,
            )
            cleaned = _BLOCK_RE.sub(" ", html_content)

            # ── Step 2: strip all remaining HTML tags ──────────────────────
            text_only = re.sub(r"<[^>]+>", " ", cleaned)

            # ── Step 3: decode HTML entities ──────────────────────────────
            text_only = html_module.unescape(text_only)

            # ── Step 4: normalise whitespace, drop trivially short lines ──
            lines: list[str] = []
            for line in re.split(r"[\r\n]+", text_only):
                line = re.sub(r"[ \t]+", " ", line).strip()
                if len(line) > 3:
                    lines.append(line)

            # ── Step 5: deduplicate (nav menus repeat identical entries) ──
            seen: set[str] = set()
            unique: list[str] = []
            for line in lines:
                if line not in seen:
                    unique.append(line)
                    seen.add(line)

            extracted = "\n".join(unique)

            if len(extracted) < 100:
                raise Exception(
                    "No readable text could be extracted from the URL "
                    f"(only {len(extracted)} chars after cleaning)."
                )

            logger.info("URL extracted %d characters from %s", len(extracted), url)
            return extracted

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
        """Chunk text semantically with overlap.

        Returns a list of dicts with 'text', 'chunk_size', and 'overlap_info' keys.
        """
        raw_chunks = SemanticChunker.chunk_text(text, overlap_percentage=overlap)
        result = []
        for idx, chunk in enumerate(raw_chunks):
            result.append({
                "text": chunk,
                "chunk_size": len(chunk),
                "overlap_info": {
                    "has_overlap": idx > 0,
                    "overlap_percentage": overlap,
                    "chunk_index": idx,
                    "total_chunks": len(raw_chunks),
                },
            })
        return result

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
