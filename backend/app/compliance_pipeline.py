"""
ESGBuddy Compliance Pipeline
Main compliance evaluation engine combining semantic retrieval, LLM, and rule validation
"""

import openai
from typing import List, Optional, Dict, Any
import logging
import json
from datetime import datetime

from app.models import (
    ESGClause,
    ClauseEvaluation,
    RetrievedEvidence,
    LLMEvaluation,
    ComplianceStatus,
    ComplianceReport,
    DocumentMetadata,
    ESGFramework
)
from app.vector_store import VectorStore
from app.rule_validator import RuleValidator
from app.config import settings

logger = logging.getLogger(__name__)


class CompliancePipeline:
    """Orchestrate the complete compliance evaluation pipeline"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.rule_validator = RuleValidator()
        self.llm_client = openai.OpenAI(api_key=settings.openai_api_key)
        self.llm_model = settings.llm_model
    
    def evaluate_document(
        self,
        document_id: str,
        clauses: List[ESGClause],
        document_metadata: DocumentMetadata,
        framework: ESGFramework
    ) -> ComplianceReport:
        """
        Evaluate a document against ESG clauses
        
        Args:
            document_id: ID of the document to evaluate
            clauses: List of ESG clauses to check
            document_metadata: Document metadata
            framework: ESG framework being evaluated
        
        Returns:
            Complete compliance report
        """
        logger.info(f"Evaluating document {document_id} against {len(clauses)} clauses")
        
        evaluations = []
        
        for clause in clauses:
            try:
                evaluation = self.evaluate_clause(document_id, clause)
                evaluations.append(evaluation)
            except Exception as e:
                logger.error(f"Error evaluating clause {clause.clause_id}: {e}")
                # Create failed evaluation
                evaluations.append(self._create_error_evaluation(clause, str(e)))
        
        # Generate summary
        summary = self._generate_summary(evaluations)
        
        # Create report
        report = ComplianceReport(
            report_id=f"report_{document_id}_{framework.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            document_id=document_id,
            document_metadata=document_metadata,
            framework=framework,
            evaluations=evaluations,
            summary=summary
        )
        
        logger.info(f"Evaluation complete: {summary}")
        
        return report
    
    def evaluate_clause(
        self,
        document_id: str,
        clause: ESGClause,
        top_k: Optional[int] = None
    ) -> ClauseEvaluation:
        """
        Evaluate a single clause against a document
        
        Pipeline:
        1. Semantic retrieval - find relevant chunks
        2. LLM evaluation - assess compliance
        3. Rule validation - deterministic checks
        4. Final decision - combine LLM + rules
        
        Args:
            document_id: Document to evaluate
            clause: ESG clause to check
            top_k: Number of chunks to retrieve
        
        Returns:
            Clause evaluation result
        """
        top_k = top_k or settings.top_k_chunks
        
        logger.debug(f"Evaluating clause {clause.clause_id}")
        
        # Step 1: Semantic Retrieval
        query = self._construct_search_query(clause)
        retrieved_evidence = self.vector_store.search_documents(
            query=query,
            document_id=document_id,
            top_k=top_k
        )
        
        if not retrieved_evidence:
            logger.warning(f"No evidence found for clause {clause.clause_id}")
            return ClauseEvaluation(
                clause_id=clause.clause_id,
                clause=clause,
                retrieved_evidence=[],
                llm_evaluation=None,
                rule_results=[],
                final_status=ComplianceStatus.NOT_SUPPORTED,
                final_confidence=0.0
            )
        
        # Step 2: LLM Evaluation
        llm_evaluation = self._evaluate_with_llm(clause, retrieved_evidence)
        
        # Step 3: Rule Validation
        rule_results = self.rule_validator.validate_rules(
            rules=clause.validation_rules,
            evidence=retrieved_evidence
        )
        
        # Step 4: Final Decision (combine LLM + rules)
        final_status, final_confidence, override_applied, override_reason = \
            self._make_final_decision(llm_evaluation, rule_results, clause)
        
        # Create evaluation
        evaluation = ClauseEvaluation(
            clause_id=clause.clause_id,
            clause=clause,
            retrieved_evidence=retrieved_evidence,
            llm_evaluation=llm_evaluation,
            rule_results=rule_results,
            final_status=final_status,
            final_confidence=final_confidence,
            override_applied=override_applied,
            override_reason=override_reason
        )
        
        return evaluation
    
    def _construct_search_query(self, clause: ESGClause) -> str:
        """Construct semantic search query from clause"""
        # Combine title, description, and keywords
        query_parts = [clause.title, clause.description]
        
        if clause.keywords:
            query_parts.append(" ".join(clause.keywords[:5]))
        
        return " ".join(query_parts)
    
    def _evaluate_with_llm(
        self,
        clause: ESGClause,
        evidence: List[RetrievedEvidence]
    ) -> LLMEvaluation:
        """
        Use GPT-4 to evaluate clause compliance
        
        Args:
            clause: ESG clause to evaluate
            evidence: Retrieved evidence chunks
        
        Returns:
            LLM evaluation result
        """
        # Construct prompt
        prompt = self._build_llm_prompt(clause, evidence)
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert ESG compliance analyst. Evaluate whether the provided evidence supports the given ESG clause requirement. Be precise and objective."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistency
                response_format={"type": "json_object"}
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            result = json.loads(response_text)
            
            # Map status string to enum
            status_map = {
                "supported": ComplianceStatus.SUPPORTED,
                "partial": ComplianceStatus.PARTIAL,
                "not_supported": ComplianceStatus.NOT_SUPPORTED,
                "inferred": ComplianceStatus.INFERRED
            }
            
            status = status_map.get(
                result.get("status", "not_supported").lower(),
                ComplianceStatus.NOT_SUPPORTED
            )
            
            return LLMEvaluation(
                status=status,
                confidence=float(result.get("confidence", 0.5)),
                explanation=result.get("explanation", ""),
                reasoning=result.get("reasoning", "")
            )
            
        except Exception as e:
            logger.error(f"LLM evaluation error: {e}")
            return LLMEvaluation(
                status=ComplianceStatus.NOT_SUPPORTED,
                confidence=0.0,
                explanation=f"LLM evaluation failed: {str(e)}",
                reasoning=""
            )
    
    def _build_llm_prompt(
        self,
        clause: ESGClause,
        evidence: List[RetrievedEvidence]
    ) -> str:
        """Build prompt for LLM evaluation"""
        
        evidence_text = "\n\n".join([
            f"[Evidence {i+1}] (Page {ev.page_number}, Similarity: {ev.similarity_score:.2f})\n{ev.text}"
            for i, ev in enumerate(evidence[:5])  # Limit to top 5 for token efficiency
        ])
        
        prompt = f"""
Evaluate whether the following evidence supports compliance with the ESG clause requirement.

**ESG Clause:**
- Framework: {clause.framework.value}
- Section: {clause.section}
- Title: {clause.title}
- Requirement: {clause.description}
- Required Evidence Type: {', '.join([et.value for et in clause.required_evidence_type])}
- Mandatory: {clause.mandatory}

**Retrieved Evidence:**
{evidence_text}

**Task:**
Determine if the evidence supports, partially supports, or does not support the clause requirement.

**Response Format (JSON):**
{{
    "status": "supported | partial | not_supported | inferred",
    "confidence": 0.0-1.0,
    "explanation": "Brief explanation of the decision (2-3 sentences)",
    "reasoning": "Detailed reasoning including specific references to evidence"
}}

**Definitions:**
- **supported**: Evidence clearly demonstrates full compliance
- **partial**: Evidence shows some compliance but is incomplete or lacks detail
- **not_supported**: No relevant evidence found or evidence contradicts requirement
- **inferred**: Compliance can be reasonably inferred but not explicitly stated

Be objective and precise. Consider the quality, completeness, and relevance of the evidence.
"""
        
        return prompt
    
    def _make_final_decision(
        self,
        llm_eval: LLMEvaluation,
        rule_results: List,
        clause: ESGClause
    ) -> tuple:
        """
        Make final compliance decision by combining LLM and rule results
        
        Rules can override LLM decisions if:
        - Mandatory rules fail
        - High-priority rules contradict LLM
        
        Returns:
            (final_status, final_confidence, override_applied, override_reason)
        """
        override_applied = False
        override_reason = None
        final_status = llm_eval.status
        final_confidence = llm_eval.confidence
        
        # Check if any mandatory rules failed
        failed_mandatory_rules = [
            r for r in rule_results
            if r.triggered and not r.passed and 
            any(vr.mandatory for vr in clause.validation_rules if vr.rule_id == r.rule_id)
        ]
        
        if failed_mandatory_rules:
            # Mandatory rule failure overrides LLM
            if llm_eval.status in [ComplianceStatus.SUPPORTED, ComplianceStatus.PARTIAL]:
                override_applied = True
                override_reason = f"Mandatory rule(s) failed: {', '.join([r.rule_id for r in failed_mandatory_rules])}"
                final_status = ComplianceStatus.PARTIAL
                final_confidence = min(final_confidence, 0.5)
        
        # Check if all rules passed but LLM said not supported
        all_rules_passed = all(r.passed for r in rule_results if r.triggered)
        if all_rules_passed and rule_results:
            if llm_eval.status == ComplianceStatus.NOT_SUPPORTED:
                # Rules suggest compliance, LLM disagrees - trust LLM but lower confidence
                final_confidence = max(0.3, final_confidence - 0.2)
        
        # Confidence calibration based on rule results
        if rule_results:
            rule_pass_rate = sum(1 for r in rule_results if r.passed) / len(rule_results)
            # Adjust confidence based on rule pass rate
            final_confidence = (final_confidence + rule_pass_rate) / 2
        
        return final_status, final_confidence, override_applied, override_reason
    
    def _generate_summary(self, evaluations: List[ClauseEvaluation]) -> Dict[str, Any]:
        """Generate summary statistics for a report"""
        
        total = len(evaluations)
        status_counts = {
            ComplianceStatus.SUPPORTED: 0,
            ComplianceStatus.PARTIAL: 0,
            ComplianceStatus.NOT_SUPPORTED: 0,
            ComplianceStatus.INFERRED: 0
        }
        
        total_confidence = 0.0
        overrides_count = 0
        
        for eval in evaluations:
            status_counts[eval.final_status] += 1
            total_confidence += eval.final_confidence
            if eval.override_applied:
                overrides_count += 1
        
        return {
            "total_clauses": total,
            "supported": status_counts[ComplianceStatus.SUPPORTED],
            "partial": status_counts[ComplianceStatus.PARTIAL],
            "not_supported": status_counts[ComplianceStatus.NOT_SUPPORTED],
            "inferred": status_counts[ComplianceStatus.INFERRED],
            "compliance_rate": (status_counts[ComplianceStatus.SUPPORTED] + 
                               status_counts[ComplianceStatus.INFERRED]) / total if total > 0 else 0.0,
            "average_confidence": total_confidence / total if total > 0 else 0.0,
            "overrides_applied": overrides_count
        }
    
    def _create_error_evaluation(self, clause: ESGClause, error: str) -> ClauseEvaluation:
        """Create an error evaluation when clause evaluation fails"""
        return ClauseEvaluation(
            clause_id=clause.clause_id,
            clause=clause,
            retrieved_evidence=[],
            llm_evaluation=LLMEvaluation(
                status=ComplianceStatus.NOT_SUPPORTED,
                confidence=0.0,
                explanation=f"Evaluation error: {error}",
                reasoning=""
            ),
            rule_results=[],
            final_status=ComplianceStatus.NOT_SUPPORTED,
            final_confidence=0.0
        )
