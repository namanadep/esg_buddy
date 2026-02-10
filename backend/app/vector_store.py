"""
ESGBuddy Vector Store Management
Handles embedding storage and semantic retrieval using ChromaDB
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional, Tuple
import logging
import gc
from pathlib import Path

from app.models import DocumentChunk, ESGClause, RetrievedEvidence
from app.config import settings
from app.ingestion import EmbeddingGenerator

logger = logging.getLogger(__name__)


class VectorStore:
    """Manage vector embeddings for semantic search"""
    
    def __init__(self):
        self.persist_directory = settings.chroma_persist_directory
        self.embedding_generator = EmbeddingGenerator()
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Collections
        self.documents_collection = None
        self.clauses_collection = None
        
        self._initialize_collections()
    
    def _initialize_collections(self):
        """Initialize or get existing collections"""
        try:
            # Documents collection
            self.documents_collection = self.client.get_or_create_collection(
                name="company_documents",
                metadata={"description": "Company ESG documents and reports"}
            )
            
            # Clauses collection
            self.clauses_collection = self.client.get_or_create_collection(
                name="esg_clauses",
                metadata={"description": "ESG standard clauses"}
            )
            
            logger.info("Vector store collections initialized")
            
        except Exception as e:
            logger.error(f"Error initializing collections: {e}")
            raise
    
    # ============= Document Operations =============
    
    def add_document_chunks(
        self, 
        chunks: List[DocumentChunk],
        batch_size: int = 100
    ) -> int:
        """
        Add document chunks to vector store
        
        Args:
            chunks: List of document chunks with embeddings
            batch_size: Batch size for adding embeddings
        
        Returns:
            Number of chunks added
        """
        logger.info(f"Adding {len(chunks)} chunks to vector store")
        
        # Generate embeddings if not present
        chunks_without_embeddings = [c for c in chunks if c.embedding is None]
        if chunks_without_embeddings:
            logger.info(f"Generating embeddings for {len(chunks_without_embeddings)} chunks")
            texts = [c.text for c in chunks_without_embeddings]
            
            # Generate in batches
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                batch_embeddings = self.embedding_generator.generate_embeddings_batch(batch_texts)
                
                for j, embedding in enumerate(batch_embeddings):
                    chunks_without_embeddings[i+j].embedding = embedding
        
        # Add to ChromaDB in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            
            ids = [c.chunk_id for c in batch]
            embeddings = [c.embedding for c in batch]
            documents = [c.text for c in batch]
            metadatas = [
                {
                    "document_id": c.document_id,
                    "page_number": c.page_number,
                    "section": c.section or "",
                    **c.metadata
                }
                for c in batch
            ]
            
            self.documents_collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
        
        logger.info(f"Successfully added {len(chunks)} chunks to vector store")
        return len(chunks)
    
    def search_documents(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RetrievedEvidence]:
        """
        Semantic search over document chunks
        
        Args:
            query: Search query text
            document_id: Filter by specific document (optional)
            top_k: Number of results to return
            filter_metadata: Additional metadata filters
        
        Returns:
            List of retrieved evidence
        """
        top_k = top_k or settings.top_k_chunks
        
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(query)
        
        # Build where clause for filtering
        where = {}
        if document_id:
            where["document_id"] = document_id
        if filter_metadata:
            where.update(filter_metadata)
        
        # Search
        results = self.documents_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where if where else None
        )
        
        # Convert to RetrievedEvidence
        evidence = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                evidence.append(RetrievedEvidence(
                    chunk_id=results['ids'][0][i],
                    text=results['documents'][0][i],
                    page_number=results['metadatas'][0][i].get('page_number', 0),
                    section=results['metadatas'][0][i].get('section'),
                    similarity_score=1 - results['distances'][0][i],  # Convert distance to similarity
                    document_id=results['metadatas'][0][i].get('document_id', '')
                ))
        
        return evidence
    
    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks for a document
        
        Returns:
            Number of chunks deleted
        """
        # Get all chunk IDs for this document
        results = self.documents_collection.get(
            where={"document_id": document_id}
        )
        
        if results['ids']:
            self.documents_collection.delete(ids=results['ids'])
            logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            return len(results['ids'])
        
        return 0
    
    # ============= Clause Operations =============
    
    def add_clauses(
        self, 
        clauses: List[ESGClause],
        batch_size: int = 20  # Reduced from 50 to reduce memory usage
    ) -> int:
        """
        Add ESG clauses to vector store
        
        Args:
            clauses: List of ESG clauses
            batch_size: Batch size for processing
        
        Returns:
            Number of clauses added
        """
        logger.info(f"Adding {len(clauses)} clauses to vector store")
        
        # Generate embeddings for clause descriptions
        clauses_without_embeddings = [c for c in clauses if c.embedding is None]
        if clauses_without_embeddings:
            logger.info(f"Generating embeddings for {len(clauses_without_embeddings)} clauses")
            
            def sanitize_for_embedding(text: str, max_chars: int = 8000) -> str:
                """Ensure text is valid for OpenAI embeddings API."""
                if text is None or not isinstance(text, str):
                    return "(no description)"
                s = str(text).strip()
                if not s:
                    return "(no description)"
                return s[:max_chars] if len(s) > max_chars else s
            
            for i in range(0, len(clauses_without_embeddings), batch_size):
                batch = clauses_without_embeddings[i:i+batch_size]
                batch_descriptions = [sanitize_for_embedding(c.description) for c in batch]
                batch_embeddings = self.embedding_generator.generate_embeddings_batch(batch_descriptions)
                
                for j, embedding in enumerate(batch_embeddings):
                    batch[j].embedding = embedding
                
                # Clear batch data after processing to free memory
                del batch_descriptions
                del batch_embeddings
                if (i // batch_size) % 5 == 0:  # GC every 5 batches
                    gc.collect()
        
        # Add to ChromaDB (use unique id per clause to avoid duplicate-id errors)
        for i in range(0, len(clauses), batch_size):
            batch = clauses[i:i+batch_size]
            
            ids = [f"{c.clause_id}_{i + j}" for j, c in enumerate(batch)]
            embeddings = [c.embedding for c in batch]
            documents = [c.description for c in batch]
            metadatas = [
                {
                    "framework": c.framework.value,
                    "section": c.section or "",
                    "title": c.title,
                    "mandatory": c.mandatory,
                    "evidence_types": ",".join([et.value for et in c.required_evidence_type]),
                    "keywords": ",".join(c.keywords),
                    "clause_id": c.clause_id,
                }
                for c in batch
            ]
            
            self.clauses_collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            # Clear batch data after adding to DB
            del ids, embeddings, documents, metadatas, batch
            if (i // batch_size) % 3 == 0:  # GC every 3 batches
                gc.collect()
        
        total_added = len(clauses)
        logger.info(f"Successfully added {total_added} clauses to vector store")
        del clauses  # Clear clauses list after processing
        gc.collect()
        return total_added
    
    def get_clause(self, clause_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific clause by ID"""
        try:
            result = self.clauses_collection.get(
                ids=[clause_id],
                include=["documents", "metadatas"]
            )
            
            if result['ids']:
                return {
                    "clause_id": result['ids'][0],
                    "description": result['documents'][0],
                    "metadata": result['metadatas'][0]
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting clause {clause_id}: {e}")
            return None
    
    def get_all_clauses(
        self, 
        framework: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all clauses, optionally filtered by framework
        
        Returns:
            List of clause dictionaries
        """
        where = {"framework": framework} if framework else None
        
        try:
            results = self.clauses_collection.get(
                where=where,
                include=["documents", "metadatas"]
            )
            
            clauses = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    clauses.append({
                        "clause_id": results['ids'][i],
                        "description": results['documents'][i],
                        "metadata": results['metadatas'][i]
                    })
            
            return clauses
            
        except Exception as e:
            logger.error(f"Error getting clauses: {e}")
            return []
    
    def clear_clauses(self, framework: Optional[str] = None):
        """Clear all clauses, optionally for a specific framework"""
        if framework:
            results = self.clauses_collection.get(where={"framework": framework})
            if results['ids']:
                self.clauses_collection.delete(ids=results['ids'])
                logger.info(f"Cleared {len(results['ids'])} clauses for {framework}")
        else:
            # Clear all
            self.client.delete_collection("esg_clauses")
            self.clauses_collection = self.client.create_collection(
                name="esg_clauses",
                metadata={"description": "ESG standard clauses"}
            )
            logger.info("Cleared all clauses")
    
    # ============= Utility Methods =============
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        docs_count = self.documents_collection.count()
        clauses_count = self.clauses_collection.count()
        
        return {
            "document_chunks": docs_count,
            "esg_clauses": clauses_count,
            "persist_directory": self.persist_directory
        }
    
    def reset(self):
        """Reset the entire vector store (use with caution!)"""
        self.client.reset()
        self._initialize_collections()
        logger.warning("Vector store has been reset")
