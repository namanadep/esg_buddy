"""
ESGBuddy Document Ingestion Module
Handles PDF parsing, chunking, and embedding generation
"""

import fitz  # PyMuPDF
import hashlib
import tiktoken
from typing import List, Tuple, Optional
from pathlib import Path
import logging
from datetime import datetime

from app.models import DocumentChunk, DocumentMetadata
from app.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process PDF documents for ESG compliance analysis"""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, int, List[Tuple[int, str]]]:
        """
        Extract clean text from PDF
        
        Returns:
            - Full text
            - Page count
            - List of (page_number, page_text) tuples
        """
        try:
            doc = fitz.open(pdf_path)
            pages = []
            full_text = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                
                # Clean the text
                text = self._clean_text(text)
                
                if text.strip():
                    pages.append((page_num + 1, text))
                    full_text.append(text)
            
            doc.close()
            
            return "\n\n".join(full_text), len(doc), pages
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        
        # Join lines intelligently
        cleaned = ' '.join(lines)
        
        # Remove multiple spaces
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    def chunk_text(
        self, 
        text: str, 
        page_number: int,
        section: Optional[str] = None
    ) -> List[Tuple[str, int, Optional[str]]]:
        """
        Chunk text into semantic chunks based on token count
        
        Returns:
            List of (chunk_text, page_number, section) tuples
        """
        # Tokenize the text
        tokens = self.tokenizer.encode(text)
        
        chunks = []
        start_idx = 0
        
        while start_idx < len(tokens):
            # Get chunk of tokens
            end_idx = start_idx + self.chunk_size
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode back to text
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunks.append((chunk_text, page_number, section))
            
            # Move forward with overlap
            start_idx = end_idx - self.chunk_overlap
        
        return chunks
    
    def process_document(
        self, 
        pdf_path: str,
        document_id: str,
        detect_sections: bool = True
    ) -> Tuple[List[DocumentChunk], DocumentMetadata]:
        """
        Process a PDF document into chunks
        
        Args:
            pdf_path: Path to PDF file
            document_id: Unique document identifier
            detect_sections: Whether to attempt section detection
        
        Returns:
            List of DocumentChunk objects and DocumentMetadata
        """
        logger.info(f"Processing document: {pdf_path}")
        
        # Extract text
        full_text, page_count, pages = self.extract_text_from_pdf(pdf_path)
        
        # Create metadata
        metadata = DocumentMetadata(
            filename=Path(pdf_path).name,
            document_type="pdf",
            page_count=page_count,
            upload_date=datetime.now()
        )
        
        # Chunk each page
        all_chunks = []
        chunk_counter = 0
        
        for page_num, page_text in pages:
            # Detect section if enabled
            section = None
            if detect_sections:
                section = self._detect_section(page_text)
            
            # Chunk the page text
            page_chunks = self.chunk_text(page_text, page_num, section)
            
            for chunk_text, page, sec in page_chunks:
                chunk_id = f"{document_id}_chunk_{chunk_counter}"
                
                chunk = DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    text=chunk_text,
                    page_number=page,
                    section=sec,
                    metadata={
                        "token_count": len(self.tokenizer.encode(chunk_text))
                    }
                )
                
                all_chunks.append(chunk)
                chunk_counter += 1
        
        logger.info(f"Created {len(all_chunks)} chunks from {page_count} pages")
        
        return all_chunks, metadata
    
    def _detect_section(self, text: str) -> Optional[str]:
        """
        Attempt to detect section name from text
        Looks for common section headers
        """
        lines = text.split('\n')[:5]  # Check first few lines
        
        # Common ESG section patterns
        section_keywords = [
            'environmental', 'social', 'governance', 
            'sustainability', 'climate', 'emissions',
            'diversity', 'employment', 'ethics', 'compliance',
            'risk', 'management', 'board', 'stakeholder'
        ]
        
        for line in lines:
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in section_keywords):
                return line.strip()[:100]  # Limit length
        
        return None
    
    def generate_document_id(self, filepath: str) -> str:
        """Generate unique document ID from filepath"""
        return hashlib.md5(filepath.encode()).hexdigest()[:16]


class EmbeddingGenerator:
    """Generate embeddings for text chunks"""
    
    def __init__(self, model: str = None):
        self.model = model or settings.embedding_model
        self._client = None
    
    @property
    def client(self):
        """Lazy load OpenAI client"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts. Each text must be non-empty and valid."""
        if not texts:
            return []
        # Ensure every item is a non-empty string (API rejects empty/invalid input)
        cleaned = []
        for t in texts:
            s = (t or "").strip() if isinstance(t, str) else str(t or "").strip()
            cleaned.append(s if s else "(no text)")
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=cleaned
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise
