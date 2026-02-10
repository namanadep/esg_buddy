"""
ESGBuddy Configuration Module
Centralized configuration management using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Keys
    openai_api_key: str
    
    # LLM Configuration
    llm_model: str = "gpt-5-nano"
    embedding_model: str = "text-embedding-3-small"
    use_llm_parsing: bool = False  # LLM parsing disabled for memory efficiency (uses regex instead)
    
    # Vector Database
    chroma_persist_directory: str = "./data/chroma_db"
    
    # Application
    environment: str = "development"
    log_level: str = "INFO"
    # Comma-separated frameworks to parse on startup (e.g. "BRSR,GRI,TCFD")
    parse_frameworks: str = "BRSR,GRI,TCFD"
    # Frameworks to always re-parse on startup (never load from DB). e.g. "GRI"
    reparse_frameworks_on_startup: str = "GRI"  # Only GRI reparses; BRSR and TCFD load from DB
    
    # Chunking Configuration
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # Retrieval Configuration
    top_k_chunks: int = 5
    confidence_threshold: float = 0.7
    
    # Storage Paths
    upload_dir: str = "./data/uploads"
    clause_db_path: str = "./data/clauses.db"
    audit_log_path: str = "./data/audit_logs"
    standards_dir: str = "../Standards"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.chroma_persist_directory,
            self.upload_dir,
            self.audit_log_path,
            Path(self.clause_db_path).parent
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
settings.ensure_directories()
