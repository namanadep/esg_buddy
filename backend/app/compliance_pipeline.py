"""
ESGBuddy Compliance Pipeline
Main compliance evaluation engine combining semantic retrieval, LLM, and rule validation
"""

import openai
import asyncio
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
    
    async def evaluate_document(
        self,
        document_id: str,
        clauses: List[ESGClause],
        document_metadata: DocumentMetadata,
        framework: ESGFramework
    ) -> ComplianceReport:
        """
        Evaluate a document against ESG clauses with parallel processing
        
        Args:
            document_id: ID of the document to evaluate
            clauses: List of ESG clauses to check
            document_metadata: Document metadata
            framework: ESG framework being evaluated
        
        Returns:
            Complete compliance report
        """
        logger.info(f"Evaluating document {document_id} against {len(clauses)} clauses (parallel={settings.parallel_clause_evaluation})")
        
        evaluations = []
        batch_size = settings.parallel_clause_evaluation
        
        # Process clauses in parallel batches
        for i in range(0, len(clauses), batch_size):
            batch = clauses[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(clauses) + batch_size - 1)//batch_size} ({len(batch)} clauses)")
            
            # Create tasks for parallel evaluation
            tasks = []
            for clause in batch:
                task = asyncio.create_task(self.evaluate_clause_async(document_id, clause))
                tasks.append(task)
            
            # Wait for all tasks in batch to complete
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error evaluating clause {batch[j].clause_id}: {result}")
                    evaluations.append(self._create_error_evaluation(batch[j], str(result)))
                else:
                    evaluations.append(result)
        
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
    
    async def evaluate_clause_async(
        self,
        document_id: str,
        clause: ESGClause,
        top_k: Optional[int] = None
    ) -> ClauseEvaluation:
        """
        Async wrapper for evaluate_clause to enable parallel processing
        """
        # Run synchronous code in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.evaluate_clause, document_id, clause, top_k)
    
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
        LLM evaluation with optional Chain-of-Thought and Self-Reflection
        
        Process (when reflection enabled):
        1. Chain-of-Thought: LLM thinks step-by-step
        2. Self-Reflection: LLM reviews its own reasoning
        3. Revision (if needed): LLM corrects identified issues
        
        Process (when reflection disabled - FAST MODE):
        1. Direct evaluation with simplified prompt
        
        Args:
            clause: ESG clause to evaluate
            evidence: Retrieved evidence chunks
        
        Returns:
            LLM evaluation result with reasoning traces
        """
        try:
            if settings.enable_reflection:
                # Full agentic workflow with reflection
                cot_result = self._chain_of_thought_reasoning(clause, evidence)
                reflection_result = self._self_reflection(clause, evidence, cot_result)
                
                if reflection_result.get("needs_revision", False):
                    logger.info(f"Reflection identified issues for {clause.clause_id}, revising...")
                    final_result = self._revise_reasoning(clause, evidence, cot_result, reflection_result)
                    revised = True
                else:
                    final_result = cot_result
                    revised = False
                
                reflection = reflection_result.get("reflection", "")
                reflection_issues = reflection_result.get("issues", [])
                reasoning_steps = cot_result.get("reasoning_steps", [])
            else:
                # Fast mode: Single LLM call without reflection
                final_result = self._fast_evaluation(clause, evidence)
                revised = False
                reflection = ""
                reflection_issues = []
                reasoning_steps = []
            
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
                reasoning_steps=reasoning_steps,
                reflection=reflection,
                reflection_issues=reflection_issues,
                revised=revised
            )
            
        except Exception as e:
            logger.error(f"LLM evaluation error: {e}")
            return LLMEvaluation(
                status=ComplianceStatus.NOT_SUPPORTED,
                confidence=0.0,
                explanation=f"LLM evaluation failed: {str(e)}",
                reasoning=""
            )
    
    def _fast_evaluation(
        self,
        clause: ESGClause,
        evidence: List[RetrievedEvidence]
    ) -> Dict[str, Any]:
        """
        Fast evaluation mode: Single LLM call with framework-specific prompt
        """
        evidence_text = "\n\n".join([
            f"[Evidence {i+1}] (Page {ev.page_number}, Score: {ev.similarity_score:.2f})\n{ev.text}"
            for i, ev in enumerate(evidence[:5])
        ])
        
        # Framework-specific prompts
        if clause.framework.value == "BRSR":
            prompt = self._get_brsr_prompt(clause, evidence_text)
            system_message = "You are a BRSR disclosure compliance expert. BRSR is about DISCLOSURE PRESENCE, not fact verification. Focus on whether the required information is disclosed, not whether it's sufficient or accurate."
        elif clause.framework.value == "GRI":
            prompt = self._get_gri_prompt(clause, evidence_text)
            system_message = "You are an ESG Compliance Analyzer for GRI. Prefer Supported when evidence substantively addresses the clause (narrative, policy, table, cross-ref). Use Inferred only when evidence is clearly indirect. Minimize Partial and Not Supported."
        else:
            prompt = self._get_default_prompt(clause, evidence_text)
            system_message = "You are an ESG compliance analyst. Be concise and objective."
        
        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _get_brsr_prompt(self, clause: ESGClause, evidence_text: str) -> str:
        """BRSR-specific prompt: disclosure presence with supported, partial, inferred, not_supported."""
        return f"""Evaluate BRSR disclosure compliance for this requirement.

**CRITICAL: BRSR is about DISCLOSURE PRESENCE, not verification of facts or adequacy.**

**Clause:** {clause.title}
**Requirement:** {clause.description}
**Framework:** BRSR (Business Responsibility & Sustainability Report)

**Evidence:**
{evidence_text}

**Your Task:** Classify the disclosure presence using the labels below.

**Labels:**
1. **Supported**: Disclosure is present (data, narrative, table, or cross-ref with page#). Includes "0", "Nil", "Not applicable" with reason. Mark as supported if ANY such disclosure exists.
2. **Partial**: Some disclosure present but a key element missing (e.g. narrative but no required number; only part of a multi-part indicator; table with gaps for this metric).
3. **Inferred**: Required disclosure not stated directly but can be reasonably inferred (e.g. broader policy/section implies it; related metric or narrative allows logical inference). Use when evidence is indirect but sufficient to infer compliance.
4. **Not Supported**: No disclosure and no explanation; field blank or question ignored.

**Rules:**
- Cross-reference to another section/page = Supported if it points to the required information.
- "Not applicable" or "NA" with reason = Supported.
- Prefer Supported when disclosure is present; use Partial when >50% present but key part missing; use Inferred when only indirect evidence; Not Supported only when truly absent.

**Response (JSON):**
{{
    "status": "supported | partial | inferred | not_supported",
    "confidence": 0.7-1.0,
    "explanation": "State what disclosure was found or missing",
    "detailed_reasoning": "Quote specific text or describe what was disclosed"
}}

**Remember:** Prefer Supported when disclosure is present. Use Partial/Inferred when disclosure is incomplete or indirect; use Not Supported only when no disclosure and no proxy."""
    
    def _get_default_prompt(self, clause: ESGClause, evidence_text: str) -> str:
        """Default prompt for non-BRSR frameworks"""
        return f"""Evaluate ESG compliance for this clause based on the evidence provided.

**Clause:** {clause.title}
**Requirement:** {clause.description}
**Framework:** {clause.framework.value}
**Required Evidence:** {', '.join([et.value for et in clause.required_evidence_type])}

**Evidence:**
{evidence_text}

**Evaluate:** Does the evidence support compliance with this requirement?

**Response (JSON):**
{{
    "status": "supported | partial | not_supported | inferred",
    "confidence": 0.0-1.0,
    "explanation": "Brief explanation (2-3 sentences)",
    "detailed_reasoning": "Specific evidence references and assessment"
}}

**Definitions:**
- supported: Evidence clearly demonstrates full compliance
- partial: Evidence shows some compliance but incomplete
- not_supported: No relevant evidence or contradicts requirement
- inferred: Compliance reasonably inferred but not explicit"""

    def _get_gri_prompt(self, clause: ESGClause, evidence_text: str) -> str:
        """GRI-specific prompt: prefer Supported when evidence substantively addresses the clause; use Inferred only for truly indirect evidence."""
        return f"""You are an ESG Compliance Analyzer scanning for GRI clauses. Classify this clause. **Prefer Supported when evidence substantively addresses the requirement**; use Inferred only when evidence is clearly indirect.

**Clause:** {clause.title}
**Requirement:** {clause.description}
**Framework:** GRI
**Section:** {clause.section}
**Required Evidence Type:** {', '.join([et.value for et in clause.required_evidence_type])}

**Evidence:**
{evidence_text}

**Labels (choose the highest that applies):**
1. **Supported** (green): Evidence substantively addresses the clause—data, narrative, policy text, table, or cross-ref with page# that covers what the requirement asks for. Use Supported whenever the evidence clearly relates to and answers the clause (even if not word-for-word). E.g. governance narrative covering the topic = Supported; "zero incidents" or "not applicable" = Supported; table with the requested info = Supported.
2. **Inferred** (blue): Use ONLY when evidence is **indirect**—e.g. one metric implying another, strategy implying future disclosure, or broader text from which compliance is a logical step away. Do NOT use Inferred just because the wording is general; if the content clearly covers the requirement, use Supported.
3. **Partial** (yellow): **RARELY**—only if >50% addressed but a key element critically missing (e.g. energy total but no renewable split).
4. **Not Supported** (red): Only for true zero evidence, explicit denial, or blank with no proxy.

**Rules:**
- **Prefer Supported**: Narrative, policy, table, or cross-ref that covers the requirement → **Supported**. Reserve Inferred for genuinely indirect/proxy evidence.
- Cross-references to other sections (CSR, MD&A) = Supported if they point to the required content.
- "Zero", "Nil", "Not applicable" with reason = Supported.
- Material topics only; no penalty for non-material.

**Response (JSON):**
{{
    "status": "supported | inferred | partial | not_supported",
    "confidence": 0.7-1.0,
    "explanation": "1-2 sentences: what evidence was found and why this label",
    "detailed_reasoning": "Quote evidence snippet + page/section + 1-sentence rationale"
}}"""

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
        
        # Framework-specific Chain-of-Thought
        if clause.framework.value == "BRSR":
            system_msg = "You are a BRSR disclosure compliance expert. BRSR is about DISCLOSURE PRESENCE. Use supported, partial, inferred, or not_supported as appropriate."
            task_steps = """
1. **Disclosure Presence**: Is the required disclosure present (text, table, number, narrative)?
2. **Cross-Reference**: Does the evidence reference another section/page for this information? → Supported if yes.
3. **Explicit NA/Nil**: "Not applicable", "Nil", "0" with reason? → Supported.
4. **Partial**: Some disclosure but key element missing (e.g. narrative but no number, or only part of indicator)? → Partial.
5. **Inferred**: Not stated directly but reasonably inferred from broader policy/section/related metric? → Inferred.
6. **Not Supported**: Only if no disclosure and no proxy. Then choose final status."""
        elif clause.framework.value == "GRI":
            system_msg = "You are an ESG Compliance Analyzer for GRI. Prefer Supported when evidence substantively addresses the clause (narrative, policy, table, cross-ref). Use Inferred only when evidence is clearly indirect (proxy metric, implied from broader text). Minimize Partial and Not Supported."
            task_steps = """
1. **Does the evidence substantively address the clause?** (narrative, policy, table, cross-ref with page#) → If yes, use **Supported**. Do not downgrade to Inferred just because wording is general.
2. **Inferred only when truly indirect**: One metric implying another, strategy implying future disclosure, or logical step away from what is stated. If the content clearly covers the requirement, use Supported.
3. **Partial**: Only if >50% addressed but a key element critically missing; use rarely.
4. **Not Supported**: Only for explicit blank, no proxy, or explicit denial.
5. **Cross-refs to other sections** = Supported when they point to the required content. Zero/Nil/NA with reason = Supported."""
        else:
            system_msg = "You are an expert ESG compliance analyst who thinks step-by-step and provides detailed reasoning."
            task_steps = """
1. **Evidence Quality**: Assess the relevance and quality of each evidence piece
2. **Requirement Matching**: Does the evidence address all aspects of the requirement?
3. **Evidence Type**: Does the evidence match the required type (numeric, descriptive, policy, etc.)?
4. **Completeness**: Are there any gaps in the evidence?
5. **Compliance Assessment**: Based on the above, what is the compliance status?"""
        
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
{task_steps}

**Response Format (JSON):**
{{
    "reasoning_steps": [
        "Step 1: ...",
        "Step 2: ...",
        "Step 3: ...",
        "Step 4: ...",
        "Step 5: ..."
    ],
    "status": "supported | partial | not_supported | inferred",
    "confidence": 0.0-1.0,
    "explanation": "Concise explanation (2-3 sentences)",
    "detailed_reasoning": "Comprehensive reasoning with evidence references"
}}

{"**BRSR REMINDER: Prefer Supported when disclosure is present; use Partial when key element missing, Inferred when only indirect evidence; Not Supported only when absent.**" if clause.framework.value == "BRSR" else "**GRI REMINDER: Prefer Supported when evidence substantively addresses the clause; use Inferred only for clearly indirect evidence. Quote evidence and page/section.**" if clause.framework.value == "GRI" else "Think carefully and be thorough. Each step should build on the previous one."}"""

        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": system_msg
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
        """Build prompt for LLM evaluation (framework-specific when applicable)."""
        evidence_text = "\n\n".join([
            f"[Evidence {i+1}] (Page {ev.page_number}, Similarity: {ev.similarity_score:.2f})\n{ev.text}"
            for i, ev in enumerate(evidence[:5])
        ])
        if clause.framework.value == "GRI":
            return self._get_gri_prompt(clause, evidence_text)
        return f"""
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
