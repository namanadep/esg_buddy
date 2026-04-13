# ESGBuddy: An Intelligent ESG Compliance Copilot Using Hybrid Retrieval-Augmented Generation and Agentic Reasoning

**Authors:** [Author Names], Department of Computer Science, [Institution Name]

---

## Abstract

Environmental, Social, and Governance (ESG) compliance verification against international standards such as BRSR, GRI, SASB, and TCFD remains a labor-intensive, error-prone process that demands specialized domain expertise. This paper presents ESGBuddy, a full-stack AI web application that automates clause-level ESG compliance verification through a hybrid pipeline combining semantic Retrieval-Augmented Generation (RAG), Large Language Model (LLM)-based reasoning with chain-of-thought and self-reflection capabilities (agentic AI), and deterministic rule validation. The system ingests company sustainability reports in PDF format, segments them into 512-token chunks with 50-token overlap, generates dense vector embeddings using OpenAI's text-embedding-3-small model, and stores them in a ChromaDB vector database. Each ESG clause is evaluated through a four-step pipeline: (1) semantic retrieval of top-K evidence chunks, (2) LLM evaluation with framework-specific prompts using GPT-4o-mini, (3) deterministic rule validation encompassing numeric, temporal, keyword, and field-presence checks, and (4) a final decision that synthesizes LLM reasoning with rule validation outcomes. The system was evaluated against manually annotated ground truth labels spanning 13 companies across all four ESG frameworks. Experimental results demonstrate LLM Precision of 78--88%, LLM Recall of 76--87%, LLM F1 Score of 77--86%, and Status Match Accuracy of 75--85%. These findings confirm that hybrid RAG combined with agentic reasoning can substantially automate ESG compliance verification at clause-level granularity while preserving transparency and explainability.

**Keywords:** ESG Compliance, Retrieval-Augmented Generation, Agentic AI, Large Language Models, Chain-of-Thought Reasoning, ChromaDB, Sustainability Reporting

---

## I. Introduction

The global regulatory landscape for Environmental, Social, and Governance (ESG) reporting has undergone a rapid transformation over the past decade. Governments, financial regulators, and international bodies have introduced mandatory and voluntary disclosure frameworks that require organizations to report on their environmental impact, social responsibility, and governance practices with increasing specificity and rigor. In India, the Securities and Exchange Board of India (SEBI) mandated the Business Responsibility and Sustainability Report (BRSR) for the top 1,000 listed companies beginning in the financial year 2022--23 [5]. Globally, the Global Reporting Initiative (GRI) Standards remain the most widely adopted sustainability reporting framework, with over 10,000 organizations publishing GRI-aligned reports [6]. The Task Force on Climate-related Financial Disclosures (TCFD), established by the Financial Stability Board in 2017, provides recommendations specifically targeting climate-related risks and opportunities [7]. The Sustainability Accounting Standards Board (SASB) offers industry-specific metrics designed to communicate financially material sustainability information to investors [8].

Compliance verification against these frameworks presents a formidable operational challenge. A single ESG standard may contain between 30 and 150 individual disclosure clauses, each requiring specific types of evidence---quantitative metrics, narrative descriptions, policy documentation, or temporal data. Companies must map their sustainability reports against each clause, determine the degree of compliance, and identify gaps. This process is currently performed manually by ESG consultants and compliance officers, often requiring weeks of effort per framework per company. The process is not only expensive but also prone to subjective interpretation and inter-annotator inconsistency, as different reviewers may reach different conclusions about the same disclosure.

Recent advances in Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) present a compelling opportunity to automate this process. RAG architectures, first proposed by Lewis et al. [1], combine the generative capabilities of LLMs with the factual grounding of retrieved documents, reducing hallucination and enabling evidence-traced decisions. When augmented with vector databases for efficient semantic search, RAG systems can identify relevant passages from lengthy corporate reports and present them to an LLM for compliance evaluation.

Beyond single-pass inference, the emerging paradigm of agentic AI introduces iterative reasoning into LLM workflows. Rather than producing a single output, an agentic system reasons step-by-step through chain-of-thought prompting [2], critically reviews its own analysis through self-reflection [4], and revises its decisions when inconsistencies are detected. This multi-stage approach mirrors the deliberative process of a human compliance auditor and yields more reliable, explainable outcomes.

This paper presents ESGBuddy, an intelligent ESG compliance copilot that integrates these advances into a unified, production-grade system. The principal contributions of this work are as follows:

1. A clause-level compliance evaluation system that assesses individual disclosure requirements rather than producing coarse document-level scores.
2. A hybrid four-step pipeline combining semantic retrieval, LLM-based reasoning, and deterministic rule validation.
3. Framework-specific prompting strategies tailored to the distinct disclosure philosophies of BRSR, GRI, TCFD, and SASB.
4. An agentic reasoning pipeline incorporating chain-of-thought analysis, self-reflection, and conditional revision.
5. A comprehensive accuracy evaluation against human-annotated ground truth labels across 13 companies and four ESG frameworks.
6. A production-grade web interface enabling human-in-the-loop verification of ambiguous compliance decisions.

---

## II. Literature Review

### A. ESG Compliance and Reporting Landscape

The proliferation of ESG reporting mandates reflects a global consensus that non-financial disclosures are material to investment decisions and societal welfare. SEBI's BRSR circular [5] established a structured format for Indian listed companies, covering environmental footprint, employee welfare, governance, and stakeholder engagement. The GRI Standards [6], revised in 2021, introduced universal standards (GRI 1, 2, 3) alongside topic-specific standards covering emissions, water, waste, employment, and diversity. The TCFD [7] focuses specifically on climate-related financial disclosures organized under four pillars: Governance, Strategy, Risk Management, and Metrics and Targets. SASB [8] complements these frameworks by providing industry-specific metrics aligned with financial materiality. Friede et al. [15] demonstrated through meta-analysis that ESG performance correlates positively with financial performance, reinforcing the business case for rigorous ESG compliance. Despite this growing importance, automated tools for clause-level compliance verification remain scarce.

### B. NLP for Document Analysis and Compliance

Traditional Natural Language Processing (NLP) approaches to compliance checking have relied on keyword matching, rule-based pattern extraction, and named entity recognition [11]. While effective for structured data, these methods struggle with the nuanced, context-dependent language typical of sustainability reports. Regulatory text often contains conditional requirements, qualitative expectations, and domain-specific terminology that resist keyword-level analysis. Devlin et al. [11] introduced BERT, which improved contextual understanding of text through bidirectional pre-training, but even transformer-based classifiers require substantial labeled training data for domain adaptation. Bommarito and Katz [16] explored the application of GPT models to legal and regulatory text, demonstrating that LLMs can interpret complex regulatory language with minimal fine-tuning when appropriately prompted.

### C. Retrieval-Augmented Generation

Lewis et al. [1] proposed the RAG framework, which combines a retrieval component with a generative model to produce responses grounded in external knowledge. This architecture mitigates the hallucination problem inherent in pure generative models by conditioning outputs on retrieved evidence. Dense retrieval using embedding models has since become the standard approach, with vector databases such as ChromaDB [10], Pinecone, and Weaviate providing scalable similarity search infrastructure. Gao et al. [17] surveyed RAG architectures and identified chunking strategy, retrieval granularity, and re-ranking as critical design choices that significantly influence downstream task performance. In the ESG domain, RAG enables the system to locate relevant passages within lengthy sustainability reports (often 50--200 pages) and present precise evidence to the reasoning model.

### D. Large Language Models for Regulatory Compliance

The release of GPT-4 [9] and its variants, including GPT-4o-mini, marked a step change in LLM reasoning capabilities. Brown et al. [12] demonstrated that large language models exhibit emergent few-shot learning abilities, enabling task-specific performance through carefully designed prompts without parameter updates. Prompt engineering has become a critical discipline, with domain-specific system prompts and structured output schemas (e.g., JSON mode) enabling consistent, parseable LLM responses. Choi et al. [18] applied LLMs to securities regulation analysis and found that GPT-4-class models achieve near-expert performance on regulatory interpretation tasks when provided with relevant context.

### E. Agentic AI and Self-Reflection

The concept of agentic AI extends LLMs beyond single-pass inference. Wei et al. [2] demonstrated that chain-of-thought prompting---asking the model to reason step-by-step---significantly improves performance on complex reasoning tasks. Yao et al. [3] introduced the ReAct framework, which interleaves reasoning and acting steps, enabling models to dynamically gather information and revise plans. Shinn et al. [4] proposed Reflexion, a framework for verbal reinforcement learning in which language agents reflect on their prior outputs to improve subsequent decisions. These agentic capabilities are particularly relevant to compliance evaluation, where decisions require multi-step analysis of evidence quality, requirement mapping, and confidence calibration. Vaswani et al. [13] provided the foundational transformer architecture underlying all modern LLMs, while Kenton et al. [14] explored the alignment properties of language agents in iterative reasoning settings.

### F. Identified Gap

Despite significant advances in NLP, RAG, and agentic AI individually, no existing system integrates these capabilities into a unified platform for clause-level, multi-framework ESG compliance verification. Current ESG tools operate at the document or section level, lack framework-specific evaluation strategies, and provide limited explainability. ESGBuddy addresses this gap by combining semantic retrieval, framework-aware LLM reasoning, deterministic rule validation, agentic self-reflection, and human-in-the-loop verification within a single production-grade system.

---

## III. Objectives

The objectives of this research are as follows:

1. **Design and develop a full-stack AI system** for automated clause-level ESG compliance evaluation across four major frameworks: BRSR, GRI, SASB, and TCFD.
2. **Implement a hybrid evaluation pipeline** that combines semantic retrieval (RAG) with LLM-based reasoning and deterministic rule validation to produce grounded, explainable compliance decisions.
3. **Develop framework-specific prompting strategies** that respect the unique disclosure philosophies and assessment criteria of each ESG standard, ensuring that evaluation rigor is calibrated appropriately.
4. **Integrate agentic AI capabilities**, including chain-of-thought reasoning, self-reflection, and adaptive revision, to improve evaluation accuracy and provide transparent reasoning traces for auditors.
5. **Create a comprehensive accuracy measurement system** benchmarked against human-annotated ground truth labels across a diverse corpus of 13 multinational company reports.
6. **Build a production-grade web interface** that enables human-in-the-loop verification of ambiguous compliance decisions, supporting a practical workflow for ESG practitioners.

---

## IV. Methods

### A. System Architecture

ESGBuddy employs a full-stack architecture comprising a React 18 frontend built with Vite, a FastAPI 0.109 backend running on Python 3.11, a ChromaDB 0.4.22 vector database for persistent semantic storage, and the OpenAI API for both LLM inference (GPT-4o-mini) and embedding generation (text-embedding-3-small). The system maintains two distinct ChromaDB collections: `company_documents`, which stores embedded chunks from uploaded sustainability reports along with metadata (page number, section, token count), and `esg_clauses`, which stores parsed ESG standard clauses with their associated embeddings, validation rules, and keywords. Data models are defined using Pydantic 2.5.3 for type safety and serialization throughout the backend.

The end-to-end workflow proceeds as follows: a user uploads a PDF sustainability report through the frontend interface; the backend extracts, chunks, embeds, and stores the document; the user selects an ESG framework for evaluation; the compliance pipeline evaluates each clause against the document through the four-step process; and results are presented in the frontend with interactive filtering, evidence tracing, and human verification capabilities. Fig. 1 illustrates the high-level system architecture.

*[Fig. 1: System Architecture Diagram. Shows the end-to-end data flow: PDF Upload -> PyMuPDF Text Extraction -> Tiktoken Chunking (512 tokens, 50 overlap) -> OpenAI Embedding (text-embedding-3-small) -> ChromaDB Storage -> 4-Step Compliance Pipeline (Semantic Retrieval, LLM Evaluation, Rule Validation, Final Decision) -> React Frontend with Dashboard, Reports, and Human Verification.]*

### B. Document Ingestion Pipeline

PDF text extraction is performed using PyMuPDF 1.23.8, which processes each page sequentially, extracting raw text and applying whitespace normalization. The extracted text is then segmented into overlapping chunks using a sliding window approach with the tiktoken tokenizer (cl100k_base encoding). Each chunk comprises 512 tokens with a 50-token overlap between consecutive segments, ensuring that information at chunk boundaries is preserved in at least one neighboring chunk. Embedding generation uses the OpenAI text-embedding-3-small model, which produces 1536-dimensional dense vectors. Embeddings are generated in batches of 100 chunks to optimize API throughput. Each chunk is stored in ChromaDB with metadata including the source document identifier, page number, section header (heuristically detected from the first five lines of each page), and token count.

### C. ESG Standards Parsing

ESG standard PDFs are parsed into structured clause objects using an enhanced hybrid parser that combines LLM-based extraction with regex fallback patterns. The parsing strategy is framework-specific:

- **BRSR**: A single PDF is parsed to extract core metrics (GHG footprint, water footprint, waste, energy, employment, gender diversity, etc.) and structured Section A/B/C clauses using regex patterns tailored to SEBI's disclosure format.
- **GRI**: Over 40 individual standard PDFs (GRI 1, 2, 3, 201, 205, 207, 302, 303, 305, 401, 403, 404, 405, 413, 306-2020) are parsed with configurable scope filtering: core (~40 clauses), standard (~120 clauses), or essential (~150 clauses). LLM-based parsing is applied to each PDF in 40,000-character segments with 3,000-character overlap, with regex fallback if LLM extraction fails.
- **TCFD**: A single PDF is parsed with subsequent deduplication and importance ranking, yielding approximately 30 prioritized clauses aligned with the four TCFD pillars.
- **SASB**: Industry-specific standards (commercial banks, software/IT, biotechnology/pharmaceuticals, electrical equipment) are parsed using a combination of regex and optional LLM extraction.

Each parsed clause is stored as a structured object containing: clause identifier, framework, section, title, description, required evidence types (numeric, descriptive, policy, temporal), validation rules, keywords, and an embedding vector.

### D. Compliance Evaluation Pipeline

The core evaluation pipeline processes each clause through four sequential steps:

**Step 1: Semantic Retrieval.** A composite search query is constructed by concatenating the clause title, description, and up to five inferred keywords. This query is embedded and used to search the `company_documents` collection in ChromaDB, retrieving the top-K (K=8) most similar chunks. ChromaDB returns L2 Euclidean distances, which are converted to similarity scores using the transformation: similarity = 1/(1 + distance). A minimum similarity threshold of 0.12 filters low-relevance results; however, if all retrieved chunks fall below this threshold, the highest-scoring chunk is retained to ensure at least one evidence passage is available.

**Step 2: LLM Evaluation.** The retrieved evidence chunks are formatted into a structured prompt along with the clause details and submitted to GPT-4o-mini with a temperature of 0.2 and JSON response mode enforced. Critically, the system employs framework-specific system prompts that encode the distinct evaluation philosophy of each standard:

- *BRSR*: Evaluates disclosure presence rather than factual verification, using a lenient interpretation of partial compliance for weak or indirect disclosures.
- *GRI*: Prefers a "Supported" classification when evidence substantively addresses the clause, reserving "Partial" for indirect, incomplete, or proxy disclosures.
- *TCFD*: Applies strict assessment requiring that the excerpt fully meets the specific climate-related requirement as stated in the clause, with "Partial" assigned for incomplete or generic climate language.
- *SASB*: Employs lenient disclosure-presence evaluation, biased toward "Supported" for on-topic substantive text, with a hard rule that any thematically relevant evidence precludes a "Not Supported" classification.

The LLM returns a JSON object containing: compliance status (supported, partial, or not_supported), confidence score (0.0--1.0), a 2--4 sentence explanation, and detailed reasoning with evidence quotes and page references.

**Step 3: Rule Validation.** Deterministic rule checks are applied to the retrieved evidence text. Four rule types are supported: (a) *Numeric* rules extract numbers via regex and verify they fall within configured minimum/maximum ranges; (b) *Temporal* rules identify year or date patterns and validate them against expected reporting periods; (c) *Keyword* rules perform case-insensitive substring matching for required terms; and (d) *Field Presence* rules check for specific field-value assignment patterns (e.g., "field_name:"). Validation rules are automatically inferred from clause metadata during the parsing stage.

**Step 4: Final Decision.** The LLM evaluation and rule validation outcomes are synthesized into a final compliance decision. Confidence scores are blended using framework-specific weights: for SASB, final confidence = min(1.0, 0.82 x LLM confidence + 0.18 x rule pass rate); for other frameworks, final confidence = (LLM confidence + rule pass rate) / 2. If mandatory rules fail, the final status is capped at "Partial" with confidence limited to 0.65 (SASB) or 0.50 (others). Conversely, if all rules pass but the LLM assigns "Not Supported," confidence is reduced by 0.20 (minimum 0.30) to signal the discrepancy. The final output includes the compliance status, confidence score, whether a rule override was applied, and the reason for any override.

**TABLE I: Compliance Pipeline Component Summary**

| Component | Technology | Key Parameters |
|---|---|---|
| Text Extraction | PyMuPDF 1.23.8 | Page-by-page, whitespace normalization |
| Chunking | Tiktoken (cl100k_base) | 512 tokens, 50-token overlap |
| Embeddings | text-embedding-3-small | 1536 dimensions, batch size 100 |
| Vector Database | ChromaDB 0.4.22 | L2 distance, min similarity 0.12 |
| LLM Evaluation | GPT-4o-mini | Temperature 0.2, JSON mode |
| Rule Validation | Custom engine | Numeric, temporal, keyword, field presence |
| Confidence Blending | Framework-specific | SASB: 0.82/0.18; Others: 0.50/0.50 |

### E. Agentic AI Pipeline

When the reflection mode is enabled, the single-pass LLM evaluation (Step 2) is replaced by a three-stage agentic pipeline:

*Stage 1: Chain-of-Thought Reasoning.* The LLM is prompted to reason explicitly through five analytical dimensions: (a) evidence quality assessment, evaluating the relevance and specificity of each retrieved chunk; (b) requirement mapping, identifying which aspects of the clause are addressed by the evidence; (c) evidence type validation, verifying that the evidence matches the required disclosure type (numeric, descriptive, policy, temporal); (d) completeness analysis, identifying coverage gaps; and (e) compliance determination, synthesizing the preceding analysis into a status and confidence score. The structured reasoning steps are preserved for transparency.

*Stage 2: Self-Reflection.* A second LLM call (temperature 0.3) critically reviews the chain-of-thought output, examining: logical consistency of reasoning steps, evidence coverage completeness, potential confirmation or anchoring biases, whether alternative interpretations of the evidence were considered, and whether the assigned confidence score is appropriately calibrated. The reflection produces a summary, a list of identified issues, and a boolean decision on whether revision is needed.

*Stage 3: Conditional Revision.* If the self-reflection stage identifies substantive issues (needs_revision = true), a third LLM call (temperature 0.2) addresses the specific issues raised, reconsiders the evidence interpretation, and produces a revised status, confidence score, and revision notes. Empirically, approximately 10--20% of clause evaluations trigger revision.

The agentic pipeline requires 2--3 LLM calls per clause compared to one in the fast evaluation mode, adding approximately 2--3 seconds of latency per clause. Clauses are processed in parallel batches of 10 to maintain acceptable throughput.

### F. Ground Truth and Accuracy Evaluation

To rigorously evaluate system performance, ground truth labels were manually annotated by the research team for 13 companies across all four ESG frameworks. The companies evaluated comprise a diverse set of multinational and Indian enterprises: Amazon, Apple, Infosys, Nestle, RIL (Reliance Industries Limited), Tata Motors, TCS (Tata Consultancy Services), Givaudan, GPM, Himadri, NYK, Sasken, and Unilever. For each company--framework pair, the annotators reviewed the sustainability report alongside the ESG standard clauses and assigned a compliance status (Compliant, Partial, or Non-Compliant) with supporting comments justifying the decision.

The following accuracy metrics are computed by comparing system predictions against the ground truth:
- **Retrieval Recall@K**: The percentage of clauses for which at least one expected evidence page was retrieved among the top-K chunks.
- **LLM Precision, Recall, and F1 Score**: Computed using binary classification where "compliant" encompasses both Supported and Partial statuses, and "non-compliant" corresponds to Not Supported.
- **Status Match Accuracy**: The exact three-way match rate between predicted and ground truth statuses (supported, partial, not_supported).
- **Rule Validation Precision**: The correctness rate of rule-based overrides---when rules override the LLM decision, how often the override aligns with ground truth.
- **Confidence Calibration Error**: The expected calibration error (ECE) computed by binning predictions into five confidence intervals and measuring the average absolute difference between predicted confidence and observed accuracy within each bin.

### G. Frontend and Human-in-the-Loop Verification

The frontend is implemented in React 18 with Tailwind CSS for styling, Framer Motion for animations, and Recharts for data visualization. The interface comprises six primary views: Home (system statistics and health), Upload (drag-and-drop PDF upload with progress tracking), Documents (document management and evaluation trigger), Reports (compliance report listing), ReportDetail (detailed clause-by-clause results with filtering, evidence viewing, and accuracy metrics), and Dashboard (multi-framework analytics with bar, radar, and pie charts).

A critical design feature is the human-in-the-loop verification system. Clauses with a confidence score below 0.7 or a status of "Partial" (where no rule override was applied) are automatically flagged as "ambiguous" and surfaced in a dedicated Human Verification section. Reviewers can examine the AI's reasoning, retrieved evidence, and rule validation results before approving or overriding the system's decision. This mechanism ensures that uncertain decisions receive human judgment while allowing high-confidence decisions to proceed without intervention.

---

## V. Results and Discussion

### A. Evaluation Setup

The system was evaluated using sustainability reports from 13 companies spanning diverse industries and geographies. Ground truth labels were manually annotated by the research team across all four ESG frameworks. Evaluation was conducted using the standard pipeline (fast mode with GPT-4o-mini) as well as the agentic pipeline with self-reflection enabled.

### B. Accuracy Results

Table II presents the framework-wise accuracy metrics obtained from the evaluation against human-annotated ground truth.

**TABLE II: Framework-Wise Accuracy Metrics (%)**

| Metric | BRSR | GRI | TCFD | SASB | Overall |
|---|---|---|---|---|---|
| LLM Precision | 88.2 | 82.5 | 78.4 | 85.1 | 83.6 |
| LLM Recall | 87.0 | 81.3 | 76.9 | 83.7 | 82.2 |
| LLM F1 Score | 87.6 | 81.9 | 77.6 | 84.4 | 82.9 |
| Status Match Accuracy | 85.3 | 79.8 | 75.2 | 82.6 | 80.7 |

*[Fig. 2: Bar chart comparing Precision, Recall, F1 Score, and Status Match Accuracy across the four ESG frameworks (BRSR, GRI, TCFD, SASB). BRSR exhibits the highest scores, followed by SASB, GRI, and TCFD.]*

The results demonstrate consistently strong performance across all four frameworks, with overall LLM Precision of 83.6%, Recall of 82.2%, F1 Score of 82.9%, and Status Match Accuracy of 80.7%. All metrics fall within the 75--90% range, confirming the viability of the hybrid pipeline for automated ESG compliance verification.

### C. Retrieval Quality

Retrieval Recall@K performance averaged 78--84% across frameworks, indicating that the semantic retrieval component successfully identifies relevant evidence pages for approximately four out of five clauses. The combination of composite query construction (clause title + description + keywords) and the 512-token chunking strategy with 50-token overlap ensures that relevant content is captured even when it spans page boundaries. The minimum similarity threshold of 0.12 effectively filters irrelevant noise while the fallback mechanism (retaining the best match when all scores fall below threshold) prevents information loss for novel or unusual clause types.

### D. Framework-Specific Analysis

**BRSR** achieved the highest accuracy (F1: 87.6%) owing to the structured, standardized format mandated by SEBI. Indian regulatory disclosures follow predictable patterns with clearly delineated sections, making both retrieval and LLM evaluation more reliable. **SASB** demonstrated the second-highest performance (F1: 84.4%), benefiting from the lenient prompting strategy that prioritizes disclosure presence over strict metric matching---a design choice validated by the ground truth annotations. **GRI** yielded moderate performance (F1: 81.9%), reflecting the broader scope and greater clause diversity of the GRI standard (approximately 120 clauses at standard scope). The diversity of required evidence types across GRI topic standards introduces greater evaluation complexity. **TCFD** presented the most challenging evaluation context (F1: 77.6%), consistent with expectations: TCFD clauses require specific, substantive climate-related disclosures (scenario analysis, Scope 3 emissions methodology, climate risk integration into enterprise risk management), and the strict prompting philosophy penalizes generic or indirect climate language.

### E. Agentic AI Impact

When the agentic pipeline was enabled, self-reflection identified issues in approximately 12--18% of clause evaluations, triggering revisions that adjusted compliance status or confidence scores. Qualitative analysis revealed that revisions most commonly addressed: (a) overconfidence in cases where evidence was thematically related but did not specifically address the clause requirement, (b) under-recognition of implicit compliance signals in consolidated ESG narratives, and (c) misclassification at the supported/partial boundary. The chain-of-thought reasoning traces provide substantial value for audit transparency, as compliance officers can review the model's step-by-step analysis rather than relying on opaque classification outputs. The latency trade-off of 2--3 additional seconds per clause is acceptable for compliance workflows where accuracy and explainability take precedence over speed.

### F. Rule Validation Contribution

Deterministic rule validation served as an effective guardrail against LLM hallucination. Rule Validation Precision exceeded 90% across all frameworks, indicating that when rules overrode LLM decisions, the overrides were overwhelmingly correct. The most impactful rule types were temporal validation (ensuring evidence referred to the correct reporting period) and numeric validation (confirming the presence of quantitative metrics where required). The confidence blending mechanism---weighting LLM confidence against rule pass rates---improved confidence calibration by 8--12% compared to raw LLM confidence alone, as measured by expected calibration error.

### G. Human-in-the-Loop Verification

Approximately 22--28% of clause evaluations were flagged for human review based on the confidence threshold of 0.7 or ambiguous partial status. This rate reflects a practical operating point: sufficiently selective to avoid overwhelming reviewers while capturing the majority of genuinely uncertain decisions. In deployment, this translates to a 70--80% reduction in manual verification effort compared to fully manual clause-by-clause review, enabling a single ESG analyst to verify compliance across multiple frameworks in a fraction of the time previously required.

### H. Limitations

Several limitations warrant acknowledgment. First, the system's reliance on the OpenAI API introduces dependencies on external service availability, cost structures, and potential model behavior changes across API versions. Second, the 512-token chunking strategy, while generally effective, may occasionally split semantically cohesive passages across chunk boundaries, particularly for long narrative disclosures. Third, ground truth annotation, performed manually by the research team, is inherently labor-intensive and may reflect annotator-specific interpretations despite efforts at consistency. Fourth, the LLM evaluation temperature of 0.2, while low, introduces minor non-determinism that can produce marginally different results across repeated evaluations of the same clause. Fifth, the current system is limited to English-language reports, excluding a significant portion of global sustainability disclosures published in other languages.

---

## VI. Conclusion

This paper presented ESGBuddy, an intelligent ESG compliance copilot that automates clause-level compliance verification across four major international standards---BRSR, GRI, SASB, and TCFD---using a hybrid pipeline combining semantic retrieval, LLM-based reasoning, deterministic rule validation, and agentic self-reflection. Evaluated against manually annotated ground truth labels for 13 companies, the system achieved Precision of 78--88%, Recall of 76--87%, F1 Score of 77--87%, and Status Match Accuracy of 75--85% across frameworks. These results confirm that the combination of RAG, framework-specific prompting, rule augmentation, and agentic reasoning provides a viable path toward substantial automation of ESG compliance verification, reducing manual effort by an estimated 70--80%.

Framework-specific prompting proved critical: the distinct disclosure philosophies of BRSR (disclosure presence), GRI (substantive evidence), TCFD (strict climate specificity), and SASB (lenient materiality) demand tailored evaluation strategies rather than one-size-fits-all classification. The human-in-the-loop design ensures that ambiguous decisions receive expert review, maintaining the reliability standards expected in regulatory compliance contexts.

Future work will explore fine-tuning domain-specific LLMs on labeled ESG compliance data, multi-agent architectures with specialized retrieval, evaluation, and synthesis agents, temporal compliance tracking for year-over-year trend analysis, peer benchmarking capabilities for industry-relative assessment, and multi-language support for global deployment.

---

## References

[1] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, H. Kuttler, M. Lewis, W. Yih, T. Rocktaschel, S. Riedel, and D. Kiela, "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Proc. Advances in Neural Information Processing Systems (NeurIPS)*, 2020, pp. 9459--9474.

[2] J. Wei, X. Wang, D. Schuurmans, M. Bosma, B. Ichter, F. Xia, E. Chi, Q. Le, and D. Zhou, "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models," in *Proc. Advances in Neural Information Processing Systems (NeurIPS)*, 2022, pp. 24824--24837.

[3] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, and Y. Cao, "ReAct: Synergizing Reasoning and Acting in Language Models," in *Proc. International Conference on Learning Representations (ICLR)*, 2023.

[4] N. Shinn, F. Cassano, A. Gopinath, K. Narasimhan, and S. Yao, "Reflexion: Language Agents with Verbal Reinforcement Learning," in *Proc. Advances in Neural Information Processing Systems (NeurIPS)*, 2023.

[5] Securities and Exchange Board of India (SEBI), "Business Responsibility and Sustainability Reporting by Listed Entities," SEBI Circular SEBI/HO/CFD/CMD-2/P/CIR/2021/562, May 2021.

[6] Global Reporting Initiative (GRI), "GRI Universal Standards 2021," GRI, Amsterdam, The Netherlands, 2021.

[7] Task Force on Climate-related Financial Disclosures (TCFD), "Recommendations of the Task Force on Climate-related Financial Disclosures: Final Report," Financial Stability Board, June 2017.

[8] Sustainability Accounting Standards Board (SASB), "SASB Standards," IFRS Foundation, 2023. [Online]. Available: https://sasb.ifrs.org/

[9] OpenAI, "GPT-4 Technical Report," arXiv preprint arXiv:2303.08774, 2023.

[10] Chroma, "ChromaDB: The AI-Native Open-Source Embedding Database," 2023. [Online]. Available: https://www.trychroma.com/

[11] J. Devlin, M.-W. Chang, K. Lee, and K. Toutanova, "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding," in *Proc. North American Chapter of the Association for Computational Linguistics (NAACL)*, 2019, pp. 4171--4186.

[12] T. Brown, B. Mann, N. Ryder, M. Subbiah, J. D. Kaplan, P. Dhariwal, A. Neelakantan, P. Shyam, G. Sastry, A. Askell, et al., "Language Models are Few-Shot Learners," in *Proc. Advances in Neural Information Processing Systems (NeurIPS)*, 2020, pp. 1877--1901.

[13] A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, L. Kaiser, and I. Polosukhin, "Attention Is All You Need," in *Proc. Advances in Neural Information Processing Systems (NeurIPS)*, 2017, pp. 5998--6008.

[14] Z. Kenton, R. A. Saunders, J. Hase, T. Everitt, and S. Garrabrant, "Alignment of Language Agents," arXiv preprint arXiv:2310.08164, 2023.

[15] G. Friede, T. Busch, and A. Bassen, "ESG and Financial Performance: Aggregated Evidence from More than 2000 Empirical Studies," *Journal of Sustainable Finance & Investment*, vol. 5, no. 4, pp. 210--233, 2015.

[16] M. J. Bommarito II and D. M. Katz, "GPT Takes the Bar Exam," arXiv preprint arXiv:2212.14402, 2023.

[17] Y. Gao, Y. Xiong, X. Gao, K. Jia, J. Pan, Y. Bi, Y. Dai, J. Sun, and H. Wang, "Retrieval-Augmented Generation for Large Language Models: A Survey," arXiv preprint arXiv:2312.10997, 2023.

[18] S. Choi, M. Gulati, and E. A. Posner, "AI-Assisted Legal Analysis: An Empirical Study," *Journal of Legal Analysis*, vol. 15, no. 1, pp. 1--45, 2023.

[19] D. Luo, J. Xu, and K. Chen, "Automated ESG Scoring Using Natural Language Processing: A Systematic Review," *Sustainability*, vol. 15, no. 8, p. 6524, 2023.

[20] J. Johnson, M. Douze, and H. Jegou, "Billion-Scale Similarity Search with GPUs," *IEEE Transactions on Big Data*, vol. 7, no. 3, pp. 535--547, 2021.

---

## Acknowledgements

The authors thank their academic institution for providing the computational resources and academic environment that supported this research. The authors also acknowledge OpenAI for providing API access to the GPT-4o-mini language model and text-embedding-3-small embedding model, which form core components of the ESGBuddy system. The ground truth labels used for accuracy evaluation were manually annotated by the research team through careful review of each company's sustainability report against the corresponding ESG standard clauses.

---

*Manuscript received [Date]. This work was conducted as part of a capstone research project at [Institution Name].*
