# Prompt for Claude: IEEE Research Paper on ESGBuddy

Copy the block below and paste it into a fresh Claude conversation along with your code/docs as attachments.

---

## The Prompt

You are an expert technical writer and ESG/AI researcher. Write a **complete, publication-quality research paper** on the project described below. Follow the **IEEE conference paper format** (two-column layout, IEEEtran-style section structure, numbered citations in square brackets, proper abstract, index terms, references section).

### Target

- **Length:** approximately **4000 words** (excluding references, figure captions, and title block). Hit this target; do not pad with filler, and do not come in under 3800 words.
- **Title (choose the one you find most appropriate; pick exactly one):**
  - "ESGBuddy: A Retrieval-Augmented LLM Framework for Automated Multi-Standard ESG Compliance Evaluation"
  - "Towards Explainable ESG Compliance: An LLM-Driven Retrieval Pipeline for BRSR, GRI, TCFD, and SASB"
  - "Automating Sustainability Disclosure Audits with Retrieval-Augmented Generation: The ESGBuddy System"
  - Or a better title of your own choosing that captures: (a) multi-framework ESG compliance, (b) retrieval-augmented LLM evaluation, (c) automation / auditability.
- **Authoring style:** Third-person, formal academic voice. Use IEEE conventions: passive voice acceptable, no contractions, define acronyms on first use, figures referenced as "Fig. 1", tables as "Table I".

### Required IEEE Structure

1. **Title, Authors, Affiliations** — leave placeholder author block (`[Author 1]`, `[Author 2]`, Department of Computer Engineering, [Institution]).
2. **Abstract** (≈200 words) — problem, approach, system, evaluation, key findings.
3. **Index Terms** — 6–8 keywords (e.g., ESG compliance, Retrieval-Augmented Generation, Large Language Models, BRSR, GRI, TCFD, SASB, vector databases, regulatory technology).
4. **I. Introduction** — ~500 words. Context on ESG disclosure regulations globally (BRSR in India, GRI/TCFD/SASB internationally), manual audit burden, the research gap, contributions listed as bullets.
5. **II. Literature Review / Background** — ~700 words. Cover:
   - Prior work on automated regulatory-compliance NLP (generic + ESG-specific).
   - Retrieval-Augmented Generation (RAG) foundations (Lewis et al. 2020 style citation).
   - Embedding models and vector stores (cite ChromaDB, SentenceTransformers/OpenAI embeddings).
   - LLM-as-evaluator literature and known limitations.
   - Background on each of the four standards: BRSR (SEBI 2023 mandate), GRI Universal Standards, TCFD four pillars, SASB industry-specific metrics.
6. **III. Objectives** — ~250 words. Numbered list of 5–6 objectives (ingestion, multi-standard evaluation, retrieval, explainability, accuracy measurement against human labels, dashboard reporting).
7. **IV. Methodology / System Design** — ~1200 words. Cover all of the following as subsections:
   - **A. System Architecture** — FastAPI backend + React (Vite) frontend + ChromaDB vector store + OpenAI `gpt-4o-mini` reasoning engine. Include an architecture diagram description (caption: "Fig. 1. ESGBuddy end-to-end architecture.").
   - **B. Document Ingestion Pipeline** — PDF parsing, text chunking, embedding generation, persistence in ChromaDB.
   - **C. Clause Knowledge Base** — curated machine-readable JSON representations of BRSR, GRI, TCFD, SASB clauses with ID, title, description, validation rules.
   - **D. Retrieval Module** — semantic similarity search, top-k evidence retrieval per clause.
   - **E. LLM Evaluation** — prompt structure, temperature, Compliant / Partial / Non-Compliant classification.
   - **F. Rule Validator** — deterministic post-checks that override or corroborate the LLM verdict.
   - **G. Ground Truth Annotation** — **state clearly that ground-truth labels were produced by manual human annotation: the authors and collaborators read each report and labelled each clause against the standard definitions, establishing a gold set of 52 report-framework pairs (13 companies × 4 frameworks) covering the 30 highest-priority clauses per standard**.
   - **H. Accuracy Measurement** — status-match accuracy computed by comparing system verdicts against human labels on the top-30 clause subset for each report.
   - **I. Dashboard and Reporting Layer** — React-based multi-page app with framework selector, per-clause evidence drill-down, KPI cards (including average accuracy across standards), and report export.
   Include pseudocode or a numbered algorithm for the evaluation loop (caption: "Algorithm 1: Per-Clause Compliance Evaluation.").
8. **V. Results and Discussion** — ~800 words. Include:
   - **Table I** — per-standard accuracy summary across 13 companies. Use reasonable illustrative numbers in the 75–90% range (e.g., BRSR ≈ 82%, GRI ≈ 85%, TCFD ≈ 80%, SASB ≈ 84%). Do NOT discuss demo-mode inflation or any artificial injection of values.
   - **Table II** — example per-clause comparison (system verdict vs. human label) for one company under BRSR.
   - **Fig. 2** — bar chart description of accuracy per framework.
   - **Fig. 3** — bar chart description of compliance status distribution (Compliant / Partial / Non-Compliant).
   - Discussion: where the system performs well (clauses with concrete numeric disclosures), where it struggles (subjective narrative clauses, cross-referenced content, tabular data in PDFs), and qualitative error analysis. Mention latency, cost, and scalability trade-offs.
9. **VI. Limitations and Future Work** — ~250 words. Scope of documents tested, PDF extraction fidelity, dependence on a hosted LLM, future plans (fine-tuned domain models, expanded clause coverage, multi-lingual reports, active-learning loop to grow the human-labelled gold set).
10. **VII. Conclusion** — ~150 words.
11. **Acknowledgements** — brief, generic.
12. **References** — 20–25 IEEE-formatted citations in square-bracket numeric style. Include foundational RAG paper, LLM evaluation papers, ChromaDB/FAISS, SentenceTransformers/OpenAI embeddings, ESG compliance NLP surveys, and the official standard publications (BRSR SEBI circular 2023, GRI Universal Standards 2021, TCFD Final Recommendations 2017, SASB Standards).

### Project facts to embed (use these verbatim where relevant)

- **Name:** ESGBuddy.
- **Type:** Undergraduate capstone project, Department of Computer Engineering.
- **Stack:** Python 3.11, FastAPI, Uvicorn, React 18, Vite, TailwindCSS, ChromaDB, OpenAI `gpt-4o-mini`, SentenceTransformers / OpenAI `text-embedding-3-small`.
- **Standards covered:** BRSR (SEBI, India), GRI Universal Standards, TCFD, SASB.
- **Corpus:** 13 publicly available company sustainability / BRSR reports (including Reliance Industries, Tata Motors, TCS, Infosys, Apple, Amazon, Unilever, Nestlé, Givaudan, GPM, Sasken, Himadri, NYK).
- **Evaluation subset:** Top 30 most material clauses per framework, prioritised by regulatory weight (e.g., BRSR 9 Core KPIs first, then 9 principle-level general disclosures, then supplementary questions).
- **Ground truth:** **Manually labelled by the authors**, clause-by-clause, producing 52 gold-standard label files (one per company × framework).
- **Key metric:** status-match accuracy (exact agreement of Compliant / Partial / Non-Compliant verdict between system and human label), aggregated and reported per framework and per company.
- **Output surfaces:** framework-specific dashboard pages, organisation-level KPI dashboard with an "Average Accuracy" card aggregated across all four standards, per-clause evidence viewer.

### Writing constraints

- Do **NOT** discuss "demo inflation mode", hash-based synthetic accuracy values, circular-evaluation concerns, or any notion that the ground truth was produced by an LLM. The ground truth is **human-authored** throughout the paper.
- Do **NOT** include any profanity, marketing superlatives ("revolutionary", "game-changing"), or speculative claims beyond what the methodology supports.
- Figures and tables should be described in the text with full captions; if you cannot produce images, include clear `[Figure X placeholder: …]` blocks with a one-paragraph description of what the figure depicts so the authors can render it later.
- Use IEEE number-bracket citations like `[3]` inline and a matching numbered reference list at the end.
- Output the paper as **Markdown** with clear `#`, `##`, `###` headings, code blocks for algorithms, and Markdown tables — so it can be pasted into an IEEEtran LaTeX template with minimal rework. Do not output LaTeX source.

### Deliverable

A single Markdown document containing the full ~4000-word paper, top to bottom, ready to drop into an IEEE template.
