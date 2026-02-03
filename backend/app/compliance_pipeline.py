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
        Agentic LLM evaluation with Chain-of-Thought and Self-Reflection
        
        Process:
        1. Chain-of-Thought: LLM thinks step-by-step
        2. Self-Reflection: LLM reviews its own reasoning
        3. Revision (if needed): LLM corrects identified issues
        
        Args:
            clause: ESG clause to evaluate
            evidence: Retrieved evidence chunks
        
        Returns:
            LLM evaluation result with reasoning traces
        """
        try:
            # Step 1: Chain-of-Thought Reasoning
            cot_result = self._chain_of_thought_reasoning(clause, evidence)
            
            # Step 2: Self-Reflection
            reflection_result = self._self_reflection(clause, evidence, cot_result)
            
            # Step 3: Decide if revision is needed
            if reflection_result.get("needs_revision", False):
                logger.info(f"Reflection identified issues for {clause.clause_id}, revising...")
                # Revise the analysis
                final_result = self._revise_reasoning(
                    clause, 
                    evidence, 
                    cot_result, 
                    reflection_result
                )
                revised = True
            else:
                # Use original analysis
                final_result = cot_result
                revised = False
            
            # Map status
            status_map = {
                "supported": ComplianceStatus.SUPPORTED,
                "partial": ComplianceStatus.PARTIAL,
                "not_supported": ComplianceStatus.NOT_SUPPORTED,
                "inferred": ComplianceStatus.INFERRED
            }
            
            status = status_map.get(
                final_result.get("status", "not_supported").lower(),
                ComplianceStatus.NOT_SUPPORTED
            )
            
            return LLMEvaluation(
                status=status,
                confidence=float(final_result.get("confidence", 0.5)),
                explanation=final_result.get("explanation", ""),
                reasoning=final_result.get("detailed_reasoning", ""),
                reasoning_steps=cot_result.get("reasoning_steps", []),
                reflection=reflection_result.get("reflection", ""),
                reflection_issues=reflection_result.get("issues", []),
                revised=revised
            )
            
        except Exception as e:
            logger.error(f"Agentic LLM evaluation error: {e}")
            return LLMEvaluation(
                status=ComplianceStatus.NOT_SUPPORTED,
                confidence=0.0,
                explanation=f"LLM evaluation failed: {str(e)}",
                reasoning=""
            )
    
    def _chain_of_thought_reasoning(
        self,
        clause: ESGClause,
        evidence: List[RetrievedEvidence]
    ) -> Dict[str, Any]:
        """
        Step 1: Chain-of-Thought reasoning
        LLM thinks through the problem step-by-step
        """
        evidence_text = "\n\n".join([
            f"[Evidence {i+1}] (Page {ev.page_number}, Similarity: {ev.similarity_score:.2f})\n{ev.text}"
            for i, ev in enumerate(evidence[:5])
        ])
        
        prompt = f"""You are an expert ESG compliance analyst. Analyze this ESG clause against the provided evidence using step-by-step reasoning.

**ESG Clause:**
- Framework: {clause.framework.value}
- Title: {clause.title}
- Requirement: {clause.description}
- Required Evidence Type: {', '.join([et.value for et in clause.required_evidence_type])}
- Mandatory: {clause.mandatory}

**Retrieved Evidence:**
{evidence_text}

**Task: Think step-by-step through the following:**

1. **Evidence Quality**: Assess the relevance and quality of each evidence piece
2. **Requirement Matching**: Does the evidence address all aspects of the requirement?
3. **Evidence Type**: Does the evidence match the required type (numeric, descriptive, policy, etc.)?
4. **Completeness**: Are there any gaps in the evidence?
5. **Compliance Assessment**: Based on the above, what is the compliance status?

**Response Format (JSON):**
{{
    "reasoning_steps": [
        "Step 1: Evidence Quality - ...",
        "Step 2: Requirement Matching - ...",
        "Step 3: Evidence Type - ...",
        "Step 4: Completeness - ...",
        "Step 5: Compliance Assessment - ..."
    ],
    "status": "supported | partial | not_supported | inferred",
    "confidence": 0.0-1.0,
    "explanation": "Concise explanation (2-3 sentences)",
    "detailed_reasoning": "Comprehensive reasoning with evidence references"
}}

Think carefully and be thorough. Each step should build on the previous one."""

        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert ESG compliance analyst who thinks step-by-step and provides detailed reasoning."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _self_reflection(
        self,
        clause: ESGClause,
        evidence: List[RetrievedEvidence],
        initial_reasoning: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 2: Self-Reflection
        LLM reviews its own reasoning and identifies potential issues
        """
        prompt = f"""You are a critical reviewer of ESG compliance analysis. Review the following analysis for potential issues or errors.

**Original ESG Clause:**
- Framework: {clause.framework.value}
- Title: {clause.title}
- Requirement: {clause.description}

**Initial Analysis:**
- Status: {initial_reasoning.get('status')}
- Confidence: {initial_reasoning.get('confidence')}
- Reasoning Steps: {json.dumps(initial_reasoning.get('reasoning_steps', []), indent=2)}
- Explanation: {initial_reasoning.get('explanation')}

**Your Task: Critically evaluate this analysis:**

1. **Logical Consistency**: Are the reasoning steps logically sound?
2. **Evidence Coverage**: Did the analysis consider all relevant evidence?
3. **Bias Check**: Are there any assumptions or biases in the reasoning?
4. **Completeness**: Did the analysis address all aspects of the clause requirement?
5. **Alternative Interpretations**: Could the evidence be interpreted differently?
6. **Confidence Calibration**: Is the confidence score appropriate for the evidence quality?

**Response Format (JSON):**
{{
    "reflection": "Overall assessment of the reasoning quality",
    "issues": [
        "Issue 1: description",
        "Issue 2: description"
    ],
    "strengths": [
        "Strength 1: description",
        "Strength 2: description"
    ],
    "needs_revision": true/false,
    "revision_suggestions": "If revision needed, what should be reconsidered?"
}}

Be thorough and critical. Identify any weaknesses in the reasoning."""

        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a critical reviewer who identifies flaws and inconsistencies in ESG compliance analysis."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _revise_reasoning(
        self,
        clause: ESGClause,
        evidence: List[RetrievedEvidence],
        initial_reasoning: Dict[str, Any],
        reflection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 3: Revision (if needed)
        LLM revises its analysis based on identified issues
        """
        evidence_text = "\n\n".join([
            f"[Evidence {i+1}] (Page {ev.page_number}, Similarity: {ev.similarity_score:.2f})\n{ev.text}"
            for i, ev in enumerate(evidence[:5])
        ])
        
        prompt = f"""You previously analyzed an ESG clause, and a critical review identified some issues. Please revise your analysis.

**ESG Clause:**
- Framework: {clause.framework.value}
- Title: {clause.title}
- Requirement: {clause.description}

**Evidence:**
{evidence_text}

**Your Initial Analysis:**
- Status: {initial_reasoning.get('status')}
- Confidence: {initial_reasoning.get('confidence')}
- Reasoning: {initial_reasoning.get('detailed_reasoning')}

**Issues Identified by Reviewer:**
{json.dumps(reflection.get('issues', []), indent=2)}

**Revision Suggestions:**
{reflection.get('revision_suggestions', 'None')}

**Task: Provide a revised analysis that addresses these issues.**

**Response Format (JSON):**
{{
    "status": "supported | partial | not_supported | inferred",
    "confidence": 0.0-1.0,
    "explanation": "Revised explanation (2-3 sentences)",
    "detailed_reasoning": "Revised comprehensive reasoning",
    "changes_made": "What was changed and why"
}}

Address the identified issues and provide a more accurate analysis."""

        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert ESG analyst who revises analysis based on critical feedback."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
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
