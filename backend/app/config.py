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
    llm_model: str = "gpt-4o-mini"  # Faster and more accurate than gpt-5-nano
    embedding_model: str = "text-embedding-3-small"
    use_llm_parsing: bool = True  # Enabled for SASB parsing
    
    # Vector Database
    chroma_persist_directory: str = "./data/chroma_db"
    
    # Application
    environment: str = "development"
    log_level: str = "INFO"
    # Comma-separated frameworks to load on startup (e.g. "BRSR,GRI,TCFD")
    parse_frameworks: str = "BRSR,GRI,TCFD,SASB"  # All frameworks enabled
    # Frameworks to always re-parse on startup (never load from DB). e.g. "GRI". Keep empty once indexed.
    reparse_frameworks_on_startup: str = ""
    # If True, parse PDFs when Chroma has no clauses for a framework. If False, only load Chroma (no startup parse).
    # Set True for a fresh install before the vector store is populated.
    parse_from_pdfs_on_startup: bool = False
    # GRI clause scope: "core" (~35-45) | "standard" (~120) | "essential" (~140-150)
    gri_scope: str = "standard"
    
    # Chunking Configuration
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # Retrieval Configuration
    top_k_chunks: int = 8  # Fetch more candidates, then filter by similarity threshold
    confidence_threshold: float = 0.7
    
    # Compliance Evaluation Configuration
    enable_reflection: bool = False  # Disable reflection for faster evaluation
    parallel_clause_evaluation: int = 10  # Number of clauses to evaluate in parallel
    # When True, API replaces ground-truth card metrics with deterministic 75–90% values (demo only).
    # SASB: also applies when Amazon/Apple/Infosys GT JSON exists on disk even if labels were not loaded via POST.
    demo_mode: bool = False
    # After each GRI compliance report is generated, write/update Company Reports/GRI Ground Truth/{Company} GRI Ground Truth.json (LLM). Set AUTO_GENERATE_GRI_GROUND_TRUTH=false to disable.
    auto_generate_gri_ground_truth: bool = True

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
