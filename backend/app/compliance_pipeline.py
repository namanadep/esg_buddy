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

# TCFD: TCFD-Checker persona; each user turn is ONE requirement row from parsed TCFD PDFs (any count—not limited to 11).
TCFD_CHECKER_SYSTEM_PROMPT = """You are TCFD-Checker, an expert auditor for Task Force on Climate-related Financial Disclosures (TCFD) compliance. You compare uploaded company reports (excerpts provided in the user message) against **individual requirements** taken from the TCFD standard text as extracted into our clause library—there may be many clauses (sub-disclosures, guidance, annex language), not only eleven rows. Your job each time is to judge **only the single requirement** described in that message.

CORE RULES
- Base analysis **only** on the evidence excerpts in the user message (from the company PDF). Quote or paraphrase with page/section references from those lines (e.g. p.12 via [Evidence n]).
- Output **only** the JSON object the user asks for: status must be exactly one of "supported", "partial", "not_supported" (same meaning as Supported / Partial / Unsupported for TCFD auditing).
- **supported**: The excerpt shows the company disclosure **fully** meets the **specific** requirement stated for this clause—all material elements present and specific enough for TCFD-style reporting (not merely a generic climate mention).
- **partial**: Mentioned but **incomplete**, boilerplate, ambiguous, or missing key elements of **this** requirement; or only indirect/generic linkage to what the clause asks.
- **not_supported**: No relevant evidence in the excerpts, or the requirement is clearly absent; do not invent or assume off-document content.
- **Materiality**: When the clause touches metrics, Scope 3, targets, or ERM integration, note in detailed_reasoning whether the document defines material climate issues (or that it does not).
- Prefer the **latest** reporting period when excerpts span multiple years. Ignore excerpts clearly unrelated to climate/TCFD context for **this** clause.

HOW TO READ EACH TASK
- Treat the **clause title and description** as the authoritative requirement for this call (they come from parsed TCFD PDFs—recommended disclosures, sub-bullets, or related standard text).
- Optionally situate the clause under the four pillars (Governance, Strategy, Risk Management, Metrics & Targets) using the clause section/title when helpful—but **never** collapse the task to “one of eleven boxes” if the written requirement is narrower or broader.

OPTIONAL THEMATIC ANCHOR (11 core recommended disclosures—use as context when a clause clearly aligns; otherwise rely on the clause text alone)
Governance a/b: board oversight; management’s role.
Strategy a/b/c: risks/opportunities over time horizons; business/strategy/financial effects; resilience / scenario analysis.
Risk Management a/b/c: identify/assess; manage/mitigate; integration into enterprise risk management.
Metrics & Targets a/b/c: metrics/KPIs; Scope 1/2 (and Scope 3 if material) + methodology; targets and performance vs targets.

EDGE CASES
- No TCFD-relevant content in excerpts for this requirement: not_supported.
- Ambiguous or generic climate language that does not address the **specific** clause: partial.
- Do not add markdown or prose outside the JSON object."""

# SASB: disclosure-presence–biased checker; lenient supported vs strict not_supported (retrieval excerpts are narrow).
SASB_CHECKER_SYSTEM_PROMPT = """You are SASB-Checker, an expert reviewer for Sustainability Accounting Standards Board (SASB)–style disclosures. You compare **short retrieved excerpts** from a company report against **one** SASB-related requirement from our clause library. Large issuers often disclose across many pages; excerpts may be incomplete—**do not treat missing numeric precision alone as failure** if the topic is clearly and substantively addressed.

CORE RULES
- Base judgment **only** on the evidence excerpts in the user message. Quote or paraphrase with page refs ([Evidence n]).
- Output JSON only: "supported", "partial", or "not_supported".

LENIENT **supported** (use often when the spirit of the requirement is met)
- **supported** if the excerpts show a **clear, substantive** response to the topic: narrative, policy, process, table, chart, **or** quantitative data—even if not every ideal field (exact SASB code, full methodology appendix, or every sub-metric) appears.
- **supported** for **good-faith disclosure**: related KPIs, aggregated metrics, directional trends, qualitative performance discussion, or **cross-references** that reasonably cover what the clause asks.
- **supported** when the company states **zero / nil / not applicable** with a short reason relevant to the clause.
- **supported** when excerpts are **on-topic and specific enough** that a reasonable investor would say the company addressed this disclosure area—not perfection.

**partial**
- Topic appears but is **thin**, **mostly boilerplate**, **tangential**, or **clearly missing** a major element the clause emphasizes (e.g. clause asks for a defined metric and excerpts only mention the theme in one sentence).

**not_supported** (rare)
- Use **only** when **no** excerpt chunk has a **plausible thematic link** to the clause (wrong topic, pure filler, or empty).
- **Hard rule:** If any chunk discusses the **same underlying theme** as the clause (e.g. energy, GHG, water, waste, safety, workforce, data security, supply chain, board, ethics—even different SASB industry wording), you **must not** output **not_supported**. Use **partial** at minimum, and **supported** if the discussion is concrete (numbers, named programs, processes, tables, or multi-sentence substance).
- Large tech and services issuers (e.g. hardware, software, IT services) often report under consolidated ESG narratives; **equivalent** disclosure counts.

BIAS: Unsure **supported** vs **partial** with substantive on-topic text → **supported**. Unsure **partial** vs **not_supported** → **partial**.

**Confidence:** For **supported** or strong **partial**, use **confidence 0.55–0.88** when evidence is substantive; reserve **below 0.4** mainly for thin **partial** or **not_supported**.

INDUSTRY CONTEXT (internal)
- Infer sector when helpful (retail/tech/financials/O&G/etc.). Clause title/description stays authoritative, but allow **equivalent** disclosures under different wording.

Output **only** the JSON object the user requests."""


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
            
            # Map status (LLM may still say "inferred" — treat as partial)
            raw = (final_result.get("status") or "not_supported").lower().strip()
            if raw == "inferred":
                raw = "partial"
            status_map = {
                "supported": ComplianceStatus.SUPPORTED,
                "partial": ComplianceStatus.PARTIAL,
                "not_supported": ComplianceStatus.NOT_SUPPORTED,
            }
            status = status_map.get(raw, ComplianceStatus.NOT_SUPPORTED)
            
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
            system_message = "You are an ESG Compliance Analyzer for GRI. Prefer Supported when evidence substantively addresses the clause. Use Partial when evidence is indirect, incomplete, or only partially addresses the requirement. Minimize Not Supported."
        elif clause.framework.value == "TCFD":
            prompt = self._get_tcfd_prompt(clause, evidence_text)
            system_message = TCFD_CHECKER_SYSTEM_PROMPT
        elif clause.framework.value == "SASB":
            prompt = self._get_sasb_prompt(clause, evidence_text)
            system_message = SASB_CHECKER_SYSTEM_PROMPT
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
        """BRSR-specific prompt: disclosure presence — use partial for incomplete OR indirect disclosure."""
        return f"""Evaluate BRSR disclosure compliance for this requirement.

**CRITICAL: BRSR is about DISCLOSURE PRESENCE, not verification of facts or adequacy.**

**Clause:** {clause.title}
**Requirement:** {clause.description}
**Framework:** BRSR (Business Responsibility & Sustainability Report)

**Evidence:**
{evidence_text}

**Your Task:** Classify using exactly THREE outcome labels (no other status exists):

**Labels:**
1. **Supported**: Clear, direct disclosure is present (data, narrative, table, or cross-ref with page# that points to the answer). Includes "0", "Nil", "Not applicable" with reason. Use when the requirement is explicitly addressed.
2. **Partial**: Use often when disclosure is weak, incomplete, or only indirect:
   - Some text related to the topic but a **key element of the requirement is missing** (e.g. narrative but no required number; only part of a multi-part indicator; table with gaps).
   - OR the answer is **only implied** by broader policy, another section, or related metrics (previously might be called "inferred") — use **Partial**, not Supported.
   - OR evidence is **tangential** or **low confidence** that the clause is fully answered.
   Aim for a meaningful share of clauses to be **Partial** when evidence is not a crisp, complete answer.
3. **Not Supported**: No relevant disclosure and no reasonable proxy; field blank or question ignored.

**Rules:**
- Cross-reference that clearly points to the required information = **Supported**.
- "Not applicable" or "NA" with reason = **Supported**.
- When unsure between Supported and weaker evidence, choose **Partial**.
- **Not Supported** only when truly absent.

**Response (JSON):**
{{
    "status": "supported | partial | not_supported",
    "confidence": 0.7-1.0,
    "explanation": "State what disclosure was found or missing",
    "detailed_reasoning": "Quote specific text or describe what was disclosed"
}}

**Remember:** Use **Partial** for incomplete AND for indirect/implied disclosure. Never use a label other than supported, partial, or not_supported."""
    
    def _get_tcfd_prompt(self, clause: ESGClause, evidence_text: str) -> str:
        """TCFD: TCFD-Checker; one extracted standard clause vs company evidence; same JSON schema."""
        return f"""Evaluate THIS **one** requirement from our TCFD clause library (text extracted from official TCFD PDFs—may be a recommended disclosure, sub-bullet, or other extracted obligation). Do not assume there are only eleven requirements; judge **only** what is written below.

**Clause ID:** {clause.clause_id}
**Title:** {clause.title}
**Section / pillar (if any):** {clause.section or "—"}
**Requirement (authoritative for this call):** {clause.description}
**Evidence-type hints:** {', '.join([et.value for et in clause.required_evidence_type]) or "descriptive"}

**Evidence excerpts from the company’s uploaded report:**
{evidence_text}

**Your task (TCFD-Checker):** Using only these excerpts, decide whether the company **fully** meets this specific requirement (supported), meets it **partially** or only generically (partial), or there is **no** adequate evidence (not_supported). Cite pages from the evidence lines. Note gaps. If useful, mention alignment with Governance / Strategy / Risk Management / Metrics & Targets—without replacing the clause text.

**Response (JSON only, exactly these keys):**
{{
    "status": "supported | partial | not_supported",
    "confidence": 0.0-1.0,
    "explanation": "2-4 sentences; what was found or missing for this requirement",
    "detailed_reasoning": "Quotes or paraphrase with page refs; materiality / ERM / scenario / metrics notes if relevant"
}}

Use only: supported, partial, not_supported (lowercase)."""

    def _get_sasb_prompt(self, clause: ESGClause, evidence_text: str) -> str:
        """SASB: lenient disclosure-presence style vs narrow retrieval excerpts."""
        return f"""Evaluate THIS **one** SASB-related requirement from our clause library (industry metrics/topics from SASB standards). The evidence below is only **retrieved chunks**—not the whole report—so treat **clear, on-topic disclosure** in those chunks as success when it substantively addresses the requirement.

**Clause ID:** {clause.clause_id}
**Title:** {clause.title}
**Section / industry topic (if any):** {clause.section or "—"}
**Requirement:** {clause.description}
**Evidence-type hints:** {', '.join([et.value for et in clause.required_evidence_type]) or "descriptive"}

**Evidence excerpts (retrieved from the company report):**
{evidence_text}

**Labeling (lenient, disclosure-oriented):**
1. **supported** — Excerpts **substantively cover** this requirement: data, narrative, policy, process, table, or reasonable cross-reference level of detail. **Do not** demand perfect SASB formatting or every optional sub-field. If the company clearly discusses the metric/topic with enough specificity for an investor, use **supported**.
2. **partial** — Related but **weak**, **very high-level**, **mostly generic**, or **missing** an obvious core part of what the clause asks.
3. **not_supported** — **Only** if excerpts do **not** meaningfully address this topic (unrelated text or empty of relevant content).

**Rules:**
- If excerpts are **on-topic** for this clause’s theme → **not_supported is not allowed**; use **partial** (thin) or **supported** (substantive).
- If torn between supported and partial and the content is substantive → **supported**.
- If torn between partial and not_supported → **partial**.

**Response (JSON only, exactly these keys):**
{{
    "status": "supported | partial | not_supported",
    "confidence": 0.0-1.0,
    "explanation": "2-4 sentences",
    "detailed_reasoning": "Brief quotes or paraphrase with page refs from evidence lines"
}}

**Confidence:** substantive supported or strong partial → prefer **0.55–0.88**; weak partial → **0.4–0.55**; not_supported or irrelevant excerpts → **0.15–0.35**.

Use only: supported, partial, not_supported (lowercase)."""

    def _get_default_prompt(self, clause: ESGClause, evidence_text: str) -> str:
        """Fallback prompt if a new framework is added without a specific checker."""
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
    "status": "supported | partial | not_supported",
    "confidence": 0.0-1.0,
    "explanation": "Brief explanation (2-3 sentences)",
    "detailed_reasoning": "Specific evidence references and assessment"
}}

**Definitions:**
- supported: Evidence clearly demonstrates full compliance
- partial: Evidence shows some compliance, is incomplete, or compliance is only indirect/implied
- not_supported: No relevant evidence or contradicts requirement"""

    def _get_gri_prompt(self, clause: ESGClause, evidence_text: str) -> str:
        """GRI-specific prompt: supported vs partial (indirect/incomplete) vs not_supported."""
        return f"""You are an ESG Compliance Analyzer scanning for GRI clauses. Classify using only: supported, partial, not_supported.

**Clause:** {clause.title}
**Requirement:** {clause.description}
**Framework:** GRI
**Section:** {clause.section}
**Required Evidence Type:** {', '.join([et.value for et in clause.required_evidence_type])}

**Evidence:**
{evidence_text}

**Labels (choose exactly one):**
1. **Supported**: Evidence substantively addresses the clause—data, narrative, policy, table, or cross-ref with page# that covers what the requirement asks for. "Zero", "Nil", "Not applicable" with reason = Supported. Cross-refs that point to the required content = Supported.
2. **Partial**: Evidence is **related but indirect**, **incomplete**, or only **partially** answers the clause (e.g. one metric implying another, broader strategy text, general narrative without the specific disclosure, or >50% addressed but a key element missing). Use Partial whenever the link to the requirement is weaker than a clear Supported case.
3. **Not Supported**: No relevant evidence, explicit denial, or blank with no proxy.

**Rules:**
- Prefer **Supported** when the requirement is clearly met; use **Partial** for indirect, implied, or incomplete coverage (do not invent a fourth label).
- Material topics only; no penalty for non-material.

**Response (JSON):**
{{
    "status": "supported | partial | not_supported",
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
            system_msg = "You are a BRSR disclosure compliance expert. BRSR is about DISCLOSURE PRESENCE. Use only supported, partial, or not_supported. Use partial for incomplete OR indirect/implied disclosure."
            task_steps = """
1. **Disclosure Presence**: Is the required disclosure present (text, table, number, narrative)?
2. **Cross-Reference**: Does the evidence reference another section/page for this information? → Supported if it clearly points to the answer.
3. **Explicit NA/Nil**: "Not applicable", "Nil", "0" with reason? → Supported.
4. **Partial**: Key element missing, OR only indirect/implied from broader policy/section/related metric, OR weak/tangential evidence → Partial.
5. **Not Supported**: Only if no disclosure and no proxy. Then choose final status."""
        elif clause.framework.value == "GRI":
            system_msg = "You are an ESG Compliance Analyzer for GRI. Use only supported, partial, or not_supported. Partial = indirect, incomplete, or partial coverage."
            task_steps = """
1. **Does the evidence substantively address the clause?** → If yes, **Supported**.
2. **Partial**: Indirect evidence, proxy metrics, implied compliance, incomplete answer, or key element missing.
3. **Not Supported**: Blank, no proxy, or explicit denial.
4. **Cross-refs** = Supported when they point to the required content. Zero/Nil/NA with reason = Supported."""
        elif clause.framework.value == "TCFD":
            system_msg = TCFD_CHECKER_SYSTEM_PROMPT
            task_steps = """
1. **Read the requirement**: Use clause title + description as the obligation (extracted TCFD text; may be granular—not limited to eleven items).
2. **Evidence-only**: What do the excerpts say? Cite page numbers from [Evidence n]. Optionally note Governance/Strategy/Risk/Metrics pillar if it helps.
3. **supported**: This specific requirement is fully and substantively met in the excerpts (not generic boilerplate alone).
4. **partial**: Mentioned but incomplete, vague, indirect, or missing elements of **this** requirement.
5. **not_supported**: No relevant excerpt evidence; do not invent. Then set confidence."""
        elif clause.framework.value == "SASB":
            system_msg = SASB_CHECKER_SYSTEM_PROMPT
            task_steps = """
1. **Clause**: What metric/topic does title + description ask for? (SASB-style, possibly another industry’s standard text.)
2. **Excerpts**: Retrieved chunks only—may be partial vs full report. What on-topic content appears? Cite [Evidence n].
3. **Substantive on-topic?** If yes → lean **supported** (data OR solid narrative/policy/process; perfection not required).
4. **partial**: Thin, boilerplate-only, or missing an obvious core ask.
5. **not_supported**: Only if **no** chunk is plausibly on-topic. Otherwise minimum **partial**. If unsure supported vs partial → supported when substantive."""
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
    "status": "supported | partial | not_supported",
    "confidence": 0.0-1.0,
    "explanation": "Concise explanation (2-3 sentences)",
    "detailed_reasoning": "Comprehensive reasoning with evidence references"
}}

{(
            "**BRSR REMINDER: Use Partial for incomplete OR indirect disclosure; Supported when clear; Not Supported only when absent.**"
            if clause.framework.value == "BRSR"
            else "**GRI REMINDER: Use Partial for indirect or incomplete coverage; Supported when the requirement is clearly met.**"
            if clause.framework.value == "GRI"
            else "**TCFD REMINDER: Judge the clause text as written; supported = fully meets that requirement from excerpts; generic = partial; no evidence = not_supported.**"
            if clause.framework.value == "TCFD"
            else "**SASB REMINDER: On-topic theme in any chunk → at least partial; not_supported only if wholly irrelevant. Favor supported when substantive.**"
            if clause.framework.value == "SASB"
            else "Think carefully and be thorough. Each step should build on the previous one."
        )}"""

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
    "status": "supported | partial | not_supported",
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
        if clause.framework.value == "TCFD":
            return self._get_tcfd_prompt(clause, evidence_text)
        if clause.framework.value == "SASB":
            return self._get_sasb_prompt(clause, evidence_text)
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
    "status": "supported | partial | not_supported",
    "confidence": 0.0-1.0,
    "explanation": "Brief explanation of the decision (2-3 sentences)",
    "reasoning": "Detailed reasoning including specific references to evidence"
}}

**Definitions:**
- **supported**: Evidence clearly demonstrates full compliance
- **partial**: Evidence shows some compliance, is incomplete, indirect, or implied
- **not_supported**: No relevant evidence found or evidence contradicts requirement

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
                cap = 0.65 if clause.framework.value == "SASB" else 0.5
                final_confidence = min(final_confidence, cap)
        
        # Check if all rules passed but LLM said not supported
        all_rules_passed = all(r.passed for r in rule_results if r.triggered)
        if all_rules_passed and rule_results:
            if llm_eval.status == ComplianceStatus.NOT_SUPPORTED:
                # Rules suggest compliance, LLM disagrees - trust LLM but lower confidence
                final_confidence = max(0.3, final_confidence - 0.2)
        
        # Confidence calibration based on rule results (SASB: keep more weight on LLM—rules are heuristic)
        if rule_results:
            rule_pass_rate = sum(1 for r in rule_results if r.passed) / len(rule_results)
            if clause.framework.value == "SASB":
                final_confidence = min(1.0, 0.82 * final_confidence + 0.18 * rule_pass_rate)
            else:
                final_confidence = (final_confidence + rule_pass_rate) / 2
        
        return final_status, final_confidence, override_applied, override_reason
    
    def _generate_summary(self, evaluations: List[ClauseEvaluation]) -> Dict[str, Any]:
        """Generate summary statistics for a report"""
        
        total = len(evaluations)
        status_counts = {
            ComplianceStatus.SUPPORTED: 0,
            ComplianceStatus.PARTIAL: 0,
            ComplianceStatus.NOT_SUPPORTED: 0,
        }
        
        total_confidence = 0.0
        overrides_count = 0
        
        for ev in evaluations:
            st = ev.final_status
            # Legacy in-memory value safety
            if st is not None and st not in status_counts:
                st = ComplianceStatus.PARTIAL
            status_counts[st] += 1
            total_confidence += ev.final_confidence
            if ev.override_applied:
                overrides_count += 1
        
        return {
            "total_clauses": total,
            "supported": status_counts[ComplianceStatus.SUPPORTED],
            "partial": status_counts[ComplianceStatus.PARTIAL],
            "not_supported": status_counts[ComplianceStatus.NOT_SUPPORTED],
            "compliance_rate": (
                status_counts[ComplianceStatus.SUPPORTED] + status_counts[ComplianceStatus.PARTIAL]
            ) / total if total > 0 else 0.0,
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
