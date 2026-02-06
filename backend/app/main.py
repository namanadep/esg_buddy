"""
ESGBuddy - Intelligent ESG Compliance Copilot
Main FastAPI Application
"""

# SQLite fix for ChromaDB on Windows
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

# Disable ChromaDB telemetry (avoids posthog errors)
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import logging
from pathlib import Path
import shutil
from datetime import datetime

from app.models import (
    DocumentUploadResponse,
    ClauseMatchRequest,
    ComplianceOverrideRequest,
    ComplianceReport,
    ESGFramework,
    ESGClause,
    GroundTruthLabel,
    ComplianceStatus
)
from app.config import settings
from app.ingestion import DocumentProcessor
from app.clause_parser_enhanced import EnhancedClauseParser
from app.vector_store import VectorStore
from app.compliance_pipeline import CompliancePipeline
from app.accuracy import AccuracyEvaluator

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ESGBuddy API",
    description="Intelligent ESG Compliance Copilot - Clause-level ESG compliance verification",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
vector_store = VectorStore()
compliance_pipeline = CompliancePipeline()
accuracy_evaluator = AccuracyEvaluator()
# Enhanced parser handles subdirectories and has LLM-based parsing option
# Controlled by USE_LLM_PARSING in .env (default: False = regex, True = LLM)
clause_parser = EnhancedClauseParser(use_llm=settings.use_llm_parsing)

# In-memory storage (replace with database in production)
documents_metadata = {}
compliance_reports = {}
parsed_clauses = {}


# ============= Startup & Health =============

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    logger.info("Starting ESGBuddy API")
    
    # Ensure directories exist
    settings.ensure_directories()
    
    # Always parse standards so parsed_clauses is populated for the /clauses API
    stats = vector_store.get_collection_stats()
    logger.info(f"Vector store stats: {stats}")
    
    try:
        clauses = clause_parser.parse_all_standards()
        if clauses:
            parsed_clauses['all'] = clauses
            for framework in ESGFramework:
                framework_clauses = [c for c in clauses if c.framework == framework]
                parsed_clauses[framework.value] = framework_clauses
            logger.info(f"Parsed {len(clauses)} clauses for API")
            
            # Only add to vector store if not already indexed (avoids re-embedding)
            if stats['esg_clauses'] == 0:
                logger.info("Indexing clauses into vector store...")
                vector_store.add_clauses(clauses)
                logger.info(f"Indexed {len(clauses)} clauses into vector store")
            else:
                logger.info("Vector store already has clauses, skipping re-index")
    except Exception as e:
        logger.error(f"Error parsing standards on startup: {e}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "application": "ESGBuddy",
        "description": "Intelligent ESG Compliance Copilot",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        stats = vector_store.get_collection_stats()
        return {
            "status": "healthy",
            "vector_store": stats,
            "documents_loaded": len(documents_metadata),
            "reports_generated": len(compliance_reports)
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )


# ============= Document Management =============

@app.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a company document (PDF) for ESG compliance analysis
    """
    logger.info(f"Uploading document: {file.filename}")
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Save uploaded file
        upload_path = Path(settings.upload_dir) / file.filename
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process document
        processor = DocumentProcessor()
        document_id = processor.generate_document_id(str(upload_path))
        
        chunks, metadata = processor.process_document(
            pdf_path=str(upload_path),
            document_id=document_id
        )
        
        # Store metadata
        documents_metadata[document_id] = metadata
        
        # Add to vector store
        vector_store.add_document_chunks(chunks)
        
        logger.info(f"Document {document_id} processed: {len(chunks)} chunks created")
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="success",
            chunks_created=len(chunks),
            message=f"Document uploaded and processed successfully"
        )
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    return {
        "documents": [
            {
                "document_id": doc_id,
                "filename": metadata.filename,
                "upload_date": metadata.upload_date.isoformat(),
                "page_count": metadata.page_count
            }
            for doc_id, metadata in documents_metadata.items()
        ]
    }


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all associated data"""
    if document_id not in documents_metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Delete from vector store
        deleted_count = vector_store.delete_document(document_id)
        
        # Delete metadata
        del documents_metadata[document_id]
        
        # Delete associated reports
        reports_to_delete = [
            report_id for report_id, report in compliance_reports.items()
            if report.document_id == document_id
        ]
        for report_id in reports_to_delete:
            del compliance_reports[report_id]
        
        logger.info(f"Deleted document {document_id}")
        
        return {
            "message": "Document deleted successfully",
            "chunks_deleted": deleted_count,
            "reports_deleted": len(reports_to_delete)
        }
        
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= ESG Clauses =============

@app.get("/clauses")
async def get_clauses(framework: Optional[str] = None):
    """
    Get all ESG clauses, optionally filtered by framework
    
    Args:
        framework: Filter by framework (BRSR, GRI, SASB, TCFD)
    """
    try:
        if framework:
            clauses = parsed_clauses.get(framework, [])
        else:
            clauses = parsed_clauses.get('all', [])
        
        return {
            "total": len(clauses),
            "framework": framework or "all",
            "clauses": [
                {
                    "clause_id": c.clause_id,
                    "framework": c.framework.value,
                    "section": c.section,
                    "title": c.title,
                    "description": c.description[:200] + "..." if len(c.description) > 200 else c.description,
                    "mandatory": c.mandatory,
                    "evidence_types": [et.value for et in c.required_evidence_type]
                }
                for c in clauses
            ]
        }
    except Exception as e:
        logger.error(f"Error getting clauses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/clauses/{clause_id}")
async def get_clause_detail(clause_id: str):
    """Get detailed information about a specific clause"""
    all_clauses = parsed_clauses.get('all', [])
    clause = next((c for c in all_clauses if c.clause_id == clause_id), None)
    
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")
    
    return {
        "clause_id": clause.clause_id,
        "framework": clause.framework.value,
        "section": clause.section,
        "title": clause.title,
        "description": clause.description,
        "mandatory": clause.mandatory,
        "evidence_types": [et.value for et in clause.required_evidence_type],
        "validation_rules": [
            {
                "rule_id": r.rule_id,
                "rule_type": r.rule_type,
                "description": r.description,
                "mandatory": r.mandatory
            }
            for r in clause.validation_rules
        ],
        "keywords": clause.keywords
    }


# ============= Compliance Evaluation =============

@app.post("/compliance/evaluate")
async def evaluate_compliance(request: ClauseMatchRequest):
    """
    Evaluate a document against ESG clauses
    
    This is the main compliance evaluation endpoint
    """
    logger.info(f"Evaluating compliance for document {request.document_id}, framework {request.framework.value}")
    
    # Validate document exists
    if request.document_id not in documents_metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Get clauses to evaluate
        if request.clause_ids:
            all_clauses = parsed_clauses.get('all', [])
            clauses = [c for c in all_clauses if c.clause_id in request.clause_ids]
        else:
            clauses = parsed_clauses.get(request.framework.value, [])
        
        if not clauses:
            raise HTTPException(status_code=400, detail="No clauses found for evaluation")
        
        # Run compliance evaluation
        metadata = documents_metadata[request.document_id]
        report = compliance_pipeline.evaluate_document(
            document_id=request.document_id,
            clauses=clauses,
            document_metadata=metadata,
            framework=request.framework
        )
        
        # Store report
        compliance_reports[report.report_id] = report
        
        logger.info(f"Compliance evaluation complete: {report.report_id}")
        
        return {
            "report_id": report.report_id,
            "document_id": report.document_id,
            "framework": report.framework.value,
            "summary": report.summary,
            "generated_at": report.generated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error evaluating compliance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/compliance/reports/{report_id}")
async def get_compliance_report(report_id: str):
    """Get a detailed compliance report"""
    if report_id not in compliance_reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = compliance_reports[report_id]
    
    return {
        "report_id": report.report_id,
        "document_id": report.document_id,
        "document_filename": report.document_metadata.filename,
        "framework": report.framework.value,
        "summary": report.summary,
        "generated_at": report.generated_at.isoformat(),
        "evaluations": [
            {
                "clause_id": e.clause_id,
                "clause_title": e.clause.title,
                "final_status": e.final_status.value,
                "final_confidence": e.final_confidence,
                "evidence_count": len(e.retrieved_evidence),
                "llm_explanation": e.llm_evaluation.explanation if e.llm_evaluation else None,
                "override_applied": e.override_applied,
                "override_reason": e.override_reason
            }
            for e in report.evaluations
        ]
    }


@app.get("/compliance/reports/{report_id}/clause/{clause_id}")
async def get_clause_evaluation_detail(report_id: str, clause_id: str):
    """Get detailed evaluation for a specific clause"""
    if report_id not in compliance_reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = compliance_reports[report_id]
    evaluation = next((e for e in report.evaluations if e.clause_id == clause_id), None)
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Clause evaluation not found")
    
    return {
        "clause": {
            "clause_id": evaluation.clause.clause_id,
            "title": evaluation.clause.title,
            "description": evaluation.clause.description,
            "framework": evaluation.clause.framework.value,
            "section": evaluation.clause.section
        },
        "final_status": evaluation.final_status.value,
        "final_confidence": evaluation.final_confidence,
        "llm_evaluation": {
            "status": evaluation.llm_evaluation.status.value,
            "confidence": evaluation.llm_evaluation.confidence,
            "explanation": evaluation.llm_evaluation.explanation,
            "reasoning": evaluation.llm_evaluation.reasoning
        } if evaluation.llm_evaluation else None,
        "retrieved_evidence": [
            {
                "chunk_id": ev.chunk_id,
                "text": ev.text,
                "page_number": ev.page_number,
                "section": ev.section,
                "similarity_score": ev.similarity_score
            }
            for ev in evaluation.retrieved_evidence
        ],
        "rule_results": [
            {
                "rule_id": r.rule_id,
                "passed": r.passed,
                "message": r.message,
                "triggered": r.triggered
            }
            for r in evaluation.rule_results
        ],
        "override_applied": evaluation.override_applied,
        "override_reason": evaluation.override_reason
    }


@app.post("/compliance/override")
async def override_clause_evaluation(request: ComplianceOverrideRequest):
    """
    Override a clause evaluation decision
    
    Allows manual correction of automated decisions
    """
    if request.report_id not in compliance_reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = compliance_reports[request.report_id]
    evaluation = next((e for e in report.evaluations if e.clause_id == request.clause_id), None)
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Clause evaluation not found")
    
    # Apply override
    old_status = evaluation.final_status
    evaluation.final_status = request.new_status
    evaluation.override_applied = True
    evaluation.override_reason = f"Manual override: {request.reason}"
    
    logger.info(f"Override applied to {request.clause_id}: {old_status} -> {request.new_status}")
    
    return {
        "message": "Override applied successfully",
        "clause_id": request.clause_id,
        "old_status": old_status.value,
        "new_status": request.new_status.value
    }


# ============= Accuracy & Benchmarking =============

@app.post("/accuracy/ground-truth")
async def add_ground_truth(labels: List[GroundTruthLabel]):
    """Add ground truth labels for accuracy measurement"""
    try:
        accuracy_evaluator.add_ground_truth(labels)
        return {
            "message": f"Added {len(labels)} ground truth labels",
            "total_labels": len(accuracy_evaluator.ground_truth)
        }
    except Exception as e:
        logger.error(f"Error adding ground truth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/accuracy/metrics/{report_id}")
async def get_accuracy_metrics(report_id: str):
    """Calculate accuracy metrics for a report"""
    if report_id not in compliance_reports:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report = compliance_reports[report_id]
    
    try:
        # Try to calculate against ground truth
        metrics = accuracy_evaluator.evaluate_accuracy(
            evaluations=report.evaluations,
            document_id=report.document_id
        )
        
        return {
            "report_id": report_id,
            "metrics": metrics.model_dump()
        }
        
    except Exception as e:
        logger.warning(f"Could not calculate accuracy metrics: {e}")
        
        # Fallback to self-benchmarking
        self_benchmark = accuracy_evaluator.generate_self_benchmark(report.evaluations)
        
        return {
            "report_id": report_id,
            "self_benchmark": self_benchmark,
            "note": "Ground truth not available, showing self-benchmark metrics"
        }


@app.get("/accuracy/benchmark")
async def get_benchmark_stats():
    """Get overall benchmarking statistics"""
    all_evaluations = []
    for report in compliance_reports.values():
        all_evaluations.extend(report.evaluations)
    
    if not all_evaluations:
        return {"message": "No evaluations available for benchmarking"}
    
    benchmark = accuracy_evaluator.generate_self_benchmark(all_evaluations)
    
    return {
        "total_reports": len(compliance_reports),
        "total_evaluations": len(all_evaluations),
        "benchmark_stats": benchmark
    }


# ============= System Management =============

@app.post("/system/reparse-standards")
async def reparse_standards(use_llm: bool = False):
    """
    Reparse all ESG standards and update the vector store
    
    Args:
        use_llm: Set to true to use LLM-based parsing (more accurate, uses tokens)
    
    Use this when standards are updated
    """
    try:
        logger.info(f"Reparsing ESG standards (LLM parsing: {use_llm})")
        
        # Clear existing clauses
        vector_store.clear_clauses()
        parsed_clauses.clear()
        
        # Create parser with specified mode
        parser = EnhancedClauseParser(use_llm=use_llm)
        
        # Parse standards
        clauses = parser.parse_all_standards()
        
        if clauses:
            parsed_clauses['all'] = clauses
            
            # Group by framework
            for framework in ESGFramework:
                framework_clauses = [c for c in clauses if c.framework == framework]
                parsed_clauses[framework.value] = framework_clauses
            
            # Add to vector store
            vector_store.add_clauses(clauses)
            
            logger.info(f"Reparsed and indexed {len(clauses)} clauses")
            
            return {
                "message": "Standards reparsed successfully",
                "total_clauses": len(clauses),
                "by_framework": {
                    framework.value: len(parsed_clauses[framework.value])
                    for framework in ESGFramework
                }
            }
        else:
            raise Exception("No clauses parsed from standards")
            
    except Exception as e:
        logger.error(f"Error reparsing standards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system/stats")
async def get_system_stats():
    """Get comprehensive system statistics"""
    vector_stats = vector_store.get_collection_stats()
    
    return {
        "vector_store": vector_stats,
        "documents": len(documents_metadata),
        "reports": len(compliance_reports),
        "clauses_parsed": len(parsed_clauses.get('all', [])),
        "ground_truth_labels": len(accuracy_evaluator.ground_truth)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
