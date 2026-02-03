"""
ESGBuddy Data Models
Pydantic models for type safety and validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class ComplianceStatus(str, Enum):
    """Clause compliance status"""
    SUPPORTED = "supported"
    PARTIAL = "partial"
    NOT_SUPPORTED = "not_supported"
    INFERRED = "inferred"


class ESGFramework(str, Enum):
    """Supported ESG frameworks"""
    BRSR = "BRSR"
    GRI = "GRI"
    SASB = "SASB"
    TCFD = "TCFD"


class EvidenceType(str, Enum):
    """Types of evidence required for compliance"""
    NUMERIC = "numeric"
    DESCRIPTIVE = "descriptive"
    POLICY = "policy"
    CERTIFICATION = "certification"
    TIMESTAMP = "timestamp"
    TABLE = "table"


# ============= Document Models =============

class DocumentMetadata(BaseModel):
    """Metadata for uploaded documents"""
    filename: str
    document_type: str
    upload_date: datetime = Field(default_factory=datetime.now)
    page_count: int
    year: Optional[int] = None
    company_name: Optional[str] = None


class DocumentChunk(BaseModel):
    """Text chunk from a document"""
    chunk_id: str
    document_id: str
    text: str
    page_number: int
    section: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


# ============= ESG Clause Models =============

class ValidationRule(BaseModel):
    """Rule-based validation logic"""
    rule_id: str
    rule_type: Literal["numeric", "temporal", "keyword", "field_presence"]
    description: str
    parameters: Dict[str, Any]
    mandatory: bool = False


class ESGClause(BaseModel):
    """Structured ESG compliance clause"""
    clause_id: str
    framework: ESGFramework
    section: Optional[str] = None
    title: str
    description: str
    required_evidence_type: List[EvidenceType]
    mandatory: bool = True
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None


# ============= Compliance Evaluation Models =============

class RetrievedEvidence(BaseModel):
    """Evidence chunk retrieved from documents"""
    chunk_id: str
    text: str
    page_number: int
    section: Optional[str] = None
    similarity_score: float
    document_id: str


class RuleValidationResult(BaseModel):
    """Result from rule-based validation"""
    rule_id: str
    passed: bool
    message: str
    triggered: bool = True


class LLMEvaluation(BaseModel):
    """LLM-based clause evaluation with agentic reasoning"""
    status: ComplianceStatus
    confidence: float
    explanation: str
    reasoning: Optional[str] = None
    # Agentic AI fields
    reasoning_steps: Optional[List[str]] = None  # Chain-of-thought steps
    reflection: Optional[str] = None  # Self-reflection on reasoning
    reflection_issues: Optional[List[str]] = None  # Issues found during reflection
    revised: bool = False  # Whether reasoning was revised after reflection


class ClauseEvaluation(BaseModel):
    """Complete evaluation for a single clause"""
    clause_id: str
    clause: ESGClause
    retrieved_evidence: List[RetrievedEvidence]
    llm_evaluation: Optional[LLMEvaluation] = None
    rule_results: List[RuleValidationResult] = Field(default_factory=list)
    final_status: ComplianceStatus
    final_confidence: float
    override_applied: bool = False
    override_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ============= Compliance Report Models =============

class ComplianceReport(BaseModel):
    """Full compliance report for a document"""
    report_id: str
    document_id: str
    document_metadata: DocumentMetadata
    framework: ESGFramework
    evaluations: List[ClauseEvaluation]
    summary: Dict[str, Any]
    generated_at: datetime = Field(default_factory=datetime.now)


# ============= Accuracy Measurement Models =============

class GroundTruthLabel(BaseModel):
    """Manually labeled ground truth for benchmarking"""
    clause_id: str
    document_id: str
    expected_status: ComplianceStatus
    expected_evidence_pages: List[int]
    notes: Optional[str] = None


class AccuracyMetrics(BaseModel):
    """System accuracy measurements"""
    retrieval_recall_at_k: float
    llm_precision: float
    llm_recall: float
    llm_f1_score: float
    rule_validation_precision: float
    confidence_calibration_error: float
    total_clauses_evaluated: int
    timestamp: datetime = Field(default_factory=datetime.now)


# ============= API Request/Response Models =============

class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    document_id: str
    filename: str
    status: str
    chunks_created: int
    message: str


class ClauseMatchRequest(BaseModel):
    """Request to match document against clauses"""
    document_id: str
    framework: ESGFramework
    clause_ids: Optional[List[str]] = None  # If None, evaluate all clauses


class ComplianceOverrideRequest(BaseModel):
    """Request to override a clause evaluation"""
    report_id: str
    clause_id: str
    new_status: ComplianceStatus
    reason: str
