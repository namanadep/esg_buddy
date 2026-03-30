# ESGBuddy — Comprehensive Technical Extraction

> Reconstruction from the repository and project chat thread. Empirical numbers in §6 are **examples from earlier sessions** unless `compliance_reports.json` is repopulated. **§10** gives paths + critical excerpts—open source files locally for full text.

---

## 1. ARCHITECTURE & SYSTEM DESIGN

### High-level architecture

- **Frontend:** React 18 + Vite + React Router + Tailwind + Framer Motion + Recharts + Axios. Calls backend via `VITE_API_URL` or default `/api` proxy.
- **Backend:** FastAPI app in `backend/app/main.py`; core modules:
  - `ingestion.py` — PDF text extraction (PyMuPDF), tiktoken chunking, `EmbeddingGenerator` (OpenAI embeddings).
  - `vector_store.py` — ChromaDB `PersistentClient`, two collections: `company_documents`, `esg_clauses`.
  - `clause_parser_enhanced.py` — Parses standards PDFs under `Standards/` into `ESGClause` objects; optional LLM-assisted parsing (`use_llm_parsing`).
  - `clause_parser.py` — Legacy/simple parser (superseded by enhanced in normal use).
  - `compliance_pipeline.py` — Retrieval → LLM (`_fast_evaluation` by default) → `RuleValidator` → `_make_final_decision` → `ComplianceReport`.
  - `rule_validator.py` — Regex/heuristic rules on combined evidence text.
  - `accuracy.py` — Ground-truth metrics + self-benchmark + demo metric hash.
  - `ground_truth_loader.py` — Loads JSON from `Company Reports/.../Ground Truth/`.
  - `gri_clause_ranking.py`, `tcfd_clause_ranking.py`, `sasb_clause_ranking.py` — Top-k sampling for GT.
  - `*_ground_truth_generator.py` — LLM-generated GT JSON (GRI/TCFD/SASB patterns).
  - `tcfd_clause_filter.py` — Post-parse TCFD dedupe/filter helpers.
- **State:** No DB for app data in production sense — **in-memory** `documents_metadata`, `compliance_reports`, `parsed_clauses` with **JSON persistence** (`documents_metadata.json`, `compliance_reports.json`). ChromaDB persists under `./data/chroma_db` (configurable). `clause_db_path` exists in settings but is only used to ensure parent dir exists (no active SQLite ORM usage found for clauses).

### Data flow: PDF → report

1. **Upload** `POST /documents/upload` → save PDF under `upload_dir` → `DocumentProcessor.process_document` → chunks with embeddings → `vector_store.add_document_chunks` → `documents_metadata` saved.
2. **Evaluate** `POST /compliance/evaluate` with `document_id` + `framework` (and optional `clause_ids`, `document_filename`) → load clauses for that framework from `parsed_clauses` → for each clause (batched async, `parallel_clause_evaluation`):
   - Build query from title + description + keywords (`_construct_search_query`).
   - `search_documents` on `company_documents` with `document_id` filter, `top_k_chunks` (default 8).
   - LLM JSON evaluation (`temperature=0.2`, `response_format=json_object`) with framework-specific system/user prompts.
   - `RuleValidator.validate_rules` on clause rules + evidence.
   - `_make_final_decision` merges rules + LLM confidence.
3. **Report** stored in `compliance_reports`, **saved to JSON**; optional background GRI auto-GT generation.

### API routes (from `main.py`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | App metadata |
| GET | `/health` | Health + vector stats |
| POST | `/documents/upload` | Multipart PDF upload |
| GET | `/documents` | List uploads |
| DELETE | `/documents/{document_id}` | Delete doc chunks + metadata + reports for that doc |
| GET | `/clauses` | List clauses (`?framework=` optional) |
| GET | `/clauses/{clause_id}` | Clause detail |
| POST | `/compliance/evaluate` | Run evaluation (`ClauseMatchRequest`) |
| GET | `/compliance/reports` | List reports |
| DELETE | `/compliance/reports` | Delete **all** reports |
| GET | `/compliance/reports/{report_id}` | Report + evaluations summary |
| GET | `/compliance/reports/{report_id}/clause/{clause_id}` | Full clause evaluation detail |
| POST | `/compliance/override` | Human override status |
| POST | `/accuracy/ground-truth` | Add GT labels |
| POST | `/accuracy/load-ground-truth` | Load GT from files |
| GET | `/accuracy/metrics/{report_id}` | Accuracy metrics (+ demo inflation if configured) |
| GET | `/accuracy/benchmark` | Benchmark |
| POST | `/system/reparse-framework` | Reparse one framework |
| POST | `/system/reparse-standards` | Reparse all enabled |
| GET | `/system/stats` | System stats |

**Representative shapes:**

- **Evaluate response:** `{ report_id, document_id, framework, summary, generated_at }` — `summary` includes `total_clauses`, `supported`, `partial`, `not_supported`, `compliance_rate`, `average_confidence`, `overrides_applied`.
- **List clauses (list view):** truncated `description (~200 chars)` in list endpoint.
- **Clause detail:** full `description`, `validation_rules`, `keywords`, etc.

### Database / storage schema

- **ChromaDB `company_documents`:** embeddings + metadata per chunk: `document_id`, `page_number`, `section`, plus chunk `metadata` (e.g. `token_count`).
- **ChromaDB `esg_clauses`:** `documents` = clause description text; metadata: `framework`, `section`, `title`, `mandatory`, `evidence_types` (comma-separated), `keywords`, `clause_id`. IDs are `"{clause_id}_{index}"` to avoid collisions.
- **Similarity:** Chroma returns **L2 distance**; app converts with `similarity = 1/(1+distance)`; **MIN_SIMILARITY = 0.12** filter; if all filtered, **keeps best match anyway**.
- **JSON files:** `backend/data/documents_metadata.json`, `backend/data/compliance_reports.json` — full `ComplianceReport` serialization via Pydantic `model_dump(mode='json')`.
- **Ground truth:** `Company Reports/{BRSR|GRI|TCFD|SASB} Ground Truth/*.json` — array of `{ clause_id, compliance_status, comments, ... }`.

### Folder structure (top level)

- `backend/app/` — Python package.
- `backend/data/` — uploads, chroma_db, JSON stores, audit_logs path.
- `frontend/src/pages/` — Home, Upload, Documents, Clauses, Reports, ReportDetail, Dashboard.
- `frontend/src/components/Layout.jsx`, `lib/api.js`, `index.css`, `tailwind.config.js`.
- `Company Reports/` — ground truth JSON (not deleted when reports cleared).
- `Standards/` — PDFs for parsing (path from `standards_dir`).

---

## 2. BACKEND IMPLEMENTATION

### Python modules (each file’s purpose)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, CORS `*`, routes, startup clause load/reparse, persistence |
| `config.py` | Pydantic `Settings` from `.env` |
| `models.py` | Pydantic models: `ESGClause`, `ComplianceReport`, `ClauseEvaluation`, etc. |
| `ingestion.py` | `DocumentProcessor`, `EmbeddingGenerator` |
| `vector_store.py` | Chroma collections, search, add/delete |
| `clause_parser_enhanced.py` | Framework PDF parsing → clauses |
| `clause_parser.py` | Legacy parser |
| `compliance_pipeline.py` | Evaluation orchestration, prompts, summary |
| `rule_validator.py` | numeric/temporal/keyword/field_presence rules |
| `accuracy.py` | Metrics, demo hash metrics |
| `ground_truth_loader.py` | Load GT JSON per framework/company |
| `gri_clause_ranking.py`, `tcfd_clause_ranking.py`, `sasb_clause_ranking.py` | Top-k clause ordering for GT |
| `gri_ground_truth_generator.py`, `tcfd_ground_truth_generator.py`, `sasb_ground_truth_generator.py` | LLM GT file writers |
| `tcfd_clause_filter.py` | TCFD clause post-processing |
| `__init__.py` | Package marker |

### PDF ingestion

- **Library:** PyMuPDF (`fitz`) — `page.get_text("text")`, per-page join, `_clean_text`.
- **Chunking:** `tiktoken` encoding `cl100k_base`; **`chunk_size` tokens = 512**, **`chunk_overlap` = 50**; sliding window `start_idx = end_idx - chunk_overlap`.
- **Section:** `_detect_section` scans first 5 lines for keywords (environmental, sustainability, …).
- **Embeddings:** OpenAI `text-embedding-3-small`; batch add with empty-string → `"(no text)"` guard; **sanitize max 8000 chars** for clause embeddings.

### Evaluation / prompts

- **Default path:** `enable_reflection: False` → **`_fast_evaluation`** only (single LLM call).
- **Reflection path (if enabled):** `_chain_of_thought_reasoning` → `_self_reflection` → optional `_revise_reasoning`.
- **LLM call (fast):** `model=settings.llm_model` (default **`gpt-4o-mini`**), **`temperature=0.2`**, **`response_format={"type": "json_object"}`**.
- **Evidence in prompt:** first **5** chunks formatted with page and score (fast mode uses similarity score label “Score” in `_fast_evaluation`).

### Confidence & review threshold

- **Config:** `confidence_threshold: 0.7` in settings (used where referenced).
- **Frontend human review:** `ReportDetail` uses **`CONFIDENCE_THRESHOLD = 0.7`** — clauses with `partial` **or** `confidence < 0.7` go to “Human verification” (unless override applied).
- **`_make_final_decision`:** Mandatory rule failure forces **PARTIAL** and caps confidence **`0.65` for SASB**, else **`0.5`**; SASB blends **`0.82 * llm + 0.18 * rule_pass_rate`** for confidence; non-SASB averages LLM confidence with rule pass rate.

### Ground truth / accuracy

- **Join key:** `f"{document_id}_{clause_id}"` (same as evaluator).
- **Retrieval recall:** fraction of GT rows where **any** retrieved page ∈ `expected_evidence_pages`.
- **LLM P/R/F1:** **Binary “compliant”** = predicted in {supported, partial} vs GT in {supported, partial}; then standard TP/FP/FN/TN formulas; F1 from precision/recall.
- **Status match:** exact enum match on `final_status` vs `expected_status` (3-way).
- **Demo metrics:** `demo_ground_truth_card_metrics(report_id)` — SHA-256 hash → **80–95%** for four fields when `inflate_demo_accuracy` and GT conditions met.

### Caching / rate limiting

- **None** explicitly in code beyond lazy OpenAI client in `EmbeddingGenerator`.

### Environment variables (names only; secrets redacted)

From `Settings`: `openai_api_key`, `llm_model`, `embedding_model`, `use_llm_parsing`, `chroma_persist_directory`, `environment`, `log_level`, `parse_frameworks`, `reparse_frameworks_on_startup`, `parse_from_pdfs_on_startup`, `gri_scope`, `chunk_size`, `chunk_overlap`, `top_k_chunks`, `confidence_threshold`, `enable_reflection`, `parallel_clause_evaluation`, `inflate_demo_accuracy`, `auto_generate_gri_ground_truth`, `upload_dir`, `clause_db_path`, `audit_log_path`, `standards_dir`.

Also referenced in code: `GRI_GT_LLM_MODEL`, `TCFD_GT_LLM_MODEL`, `SASB_GT_LLM_MODEL`, `ANONYMIZED_TELEMETRY` (set in `main.py`).

### Python packages

See `backend/requirements.txt` (FastAPI, uvicorn, chromadb, openai, PyMuPDF, sentence-transformers, torch, pandas, tiktoken, sqlalchemy, etc.).

---

## 3. FRONTEND IMPLEMENTATION

### Components / pages

- **`App.jsx`:** Routes: `/`, `/dashboard`, `/upload`, `/documents`, `/clauses`, `/reports`, `/reports/:reportId`.
- **`Layout.jsx`:** Nav (Home … Dashboard), health pill, footer; **`LayoutDashboard`** icon for Dashboard.
- **`Home.jsx`:** Hero, features, `getSystemStats`.
- **`Upload.jsx`:** Drag/drop, progress, `uploadDocument` → navigate `/documents`.
- **`Documents.jsx`:** List, filters/sort, `evaluateCompliance`, `deleteDocument`.
- **`Clauses.jsx`:** Framework pills, search, sort/filter panel, expandable rows, `getClauseDetail`.
- **`Reports.jsx`:** List compliance reports from API.
- **`ReportDetail.jsx`:** Summary, filter by status, expandable clause rows, **Human verification** (ambiguous = partial or low confidence), override thumbs, accuracy card, `getAccuracyMetrics`.
- **`Dashboard.jsx`:** Company selector from filenames, Recharts bar/radar/stacked pie, links to reports.
- **`main.jsx`:** React root.

### State

- **Plain React `useState` / `useEffect`** — no Redux/Zustand/Context for global app state.

### API layer

- **`frontend/src/lib/api.js`** — Axios instance `baseURL: import.meta.env.VITE_API_URL || '/api'`; wrappers for upload, documents, clauses, compliance, accuracy, system, **`deleteAllComplianceReports`**.

### Styling

- **Tailwind** with extended theme: `forest`, `clay`, `ink`, `font-display` (Playfair Display), `font-sans` (DM Sans), `gradient-forest`, `gradient-radial` in `index.css`.

### Upload

- **Upload.jsx:** Validates PDF type, progress callback on POST, 2s delay then `navigate('/documents')`.

### Report / verification

- **ReportDetail:** Loads report + accuracy; **`overrideClauseEvaluation(reportId, clauseId, newStatus, reason)`** POST body matches `ComplianceOverrideRequest` in backend.

---

## 4. FRAMEWORK-SPECIFIC LOGIC

### BRSR

- **Philosophy:** Disclosure **presence**, not fact verification (`_get_brsr_prompt` + system string in `_fast_evaluation`).
- **Parsing:** BRSR PDFs under standards path; clause structures from `clause_parser_enhanced` (BRSR-specific paths in file).

### GRI

- **`gri_scope`:** `core` | `standard` | `essential` — filters which GRI PDF filenames are parsed (`_filter_gri_pdfs_by_scope` in enhanced parser). **Standard** target ~120 PDFs (comment in code); **core** only GRI 1/2/3 patterns; **essential** adds more standards.
- **Prompt:** Substantive vs partial vs not supported; minimize not supported (`_get_gri_prompt`).
- **Auto GT:** After GRI evaluation, optional background `run_auto_gri_ground_truth_after_evaluation` if `auto_generate_gri_ground_truth` and company mapping matches.

### TCFD

- **Implemented:** Full pipeline with **`TCFD_CHECKER_SYSTEM_PROMPT`** + **`_get_tcfd_prompt`**; clauses from parsed TCFD PDFs; **`tcfd_clause_filter.py`** for dedupe/ranking for GT; **`tcfd_clause_ranking.py`** top-30 for GT alignment.
- **Prompt theme:** Per-clause requirement from extracted PDF text (explicitly **not** limited to 11 disclosures in wording).

### SASB

- **Implemented:** SASB PDF set filtered to a **small subset** of “essential” industry standards in parser; clauses like `SASB_{metric_id}` with `-` → `_`.
- **`SASB_CHECKER_SYSTEM_PROMPT` + `_get_sasb_prompt`:** Lenient supported/partial; **on-topic → not `not_supported`**; confidence blend with rules; mandatory rule fail cap **0.65**.

### Evaluation-time framework selection

- **POST `/compliance/evaluate`** `framework` field selects `parsed_clauses[framework.value]` unless `clause_ids` overrides with explicit subset from `all`.

---

## 5. AGENTIC AI PIPELINE (single clause)

1. **`_construct_search_query`:** `title + description + first 5 keywords`.
2. **`vector_store.search_documents(query, document_id, top_k)`** — `top_k` default **`settings.top_k_chunks` (= 8)**.
3. **Similarity:** `1/(1+L2_distance)`; filter `< 0.12` dropped unless nothing left → keep rank-1.
4. **`_fast_evaluation`:** Framework branch → system + user prompt → **`chat.completions.create`** `temperature=0.2`, JSON mode.
5. **Reflection (if `enable_reflection`):** CoT JSON → reflection JSON (`temperature=0.3`) → optional revision (`temperature=0.2`).
6. **Parse:** Map status string; **`inferred` → `partial`**.
7. **Rules:** `RuleValidator` on combined evidence text.
8. **`_make_final_decision`:** Merge as described.

**Verbatim prompts** are in `compliance_pipeline.py` for `TCFD_CHECKER_SYSTEM_PROMPT`, `SASB_CHECKER_SYSTEM_PROMPT`, `_get_brsr_prompt`, `_get_gri_prompt`, `_get_tcfd_prompt`, `_get_sasb_prompt`, `_chain_of_thought_reasoning`, `_self_reflection`, `_revise_reasoning` — copy from that file (lines ~29–830).

---

## 6. DATA & RESULTS

- **Current repo state:** **`compliance_reports.json` may be empty** if reports were bulk-deleted; **no live report metrics** unless you re-run evaluations.
- **Historical examples (from chat / screenshots):** SASB runs with **77 clauses**, example compliance **~96–99%**, average confidence **~60–63%**; SASB GT **status match accuracy** examples **~47–70%** vs LLM F1 **~0.95+** (different definitions).
- **Ground truth files** can remain under `Company Reports/` (JSON files).
- **Processing times:** Not instrumented as end-to-end timers in code reviewed; parallel batch size **10** clauses.

---

## 7. CONFIGURATION & DEPLOYMENT

- **Backend:** Typically `uvicorn app.main:app` from `backend` with `.env` (`OPENAI_API_KEY` required).
- **Frontend:** `npm run dev` — **Vite port 3000**, **proxies `/api` → `http://localhost:8000`** with path rewrite stripping `/api` (backend routes have **no** `/api` prefix).
- **Docker:** Verify with repo `Dockerfile` if present (not confirmed in extraction pass).
- **CORS:** `allow_origins=["*"]` in `main.py`.

---

## 8. KEY DECISIONS & TRADEOFFS

- **gpt-4o-mini:** Comment in config: faster/cost vs larger models; used as default LLM.
- **ChromaDB:** Persistent local, simple Python API; telemetry disabled.
- **512 tokens:** Balance context vs granularity; 50 overlap reduces boundary cuts.
- **L2 + `1/(1+d)`:** Standard distance-to-similarity heuristic; **0.12** floor avoids empty evidence; fallback keeps top-1.
- **Reflection off by default:** Speed.
- **SASB leniency:** Retrieval excerpts narrow → prompts and confidence tuned so large issuers don’t get crushed.

---

## 9. BUGS / ISSUES (from shared history)

| Symptom | Cause | Fix / mitigation |
|---------|--------|------------------|
| Chroma/SQLite on Windows | Default sqlite | `pysqlite3` swap in `main.py` |
| Missing `pydantic-settings` | Import error | `pip install pydantic-settings` |
| Empty embedding batch | OpenAI rejects empty strings | Replace with `"(no text)"` in batch |
| Filename “Pineapple” vs “Apple” | Substring `APPLE` | Token-based company detection for SASB/GT |
| Long LLM GT generation | Timeout in sandbox | Run locally / background |
| Reports removed but GT files wanted | Separate paths | GT JSON kept; only evaluator keys pruned for deleted doc IDs |

---

## 10. CODE SNIPPETS (critical excerpts — see files for full text)

### FastAPI entry / CORS / sqlite hack

```python
# main.py (excerpt)
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
# ...
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```

### L2 → similarity

```python
# vector_store.py (excerpt)
dist = float(results['distances'][0][i])
similarity_score = 1.0 / (1.0 + dist)
MIN_SIMILARITY = 0.12
```

### Evaluate clause core

```python
# compliance_pipeline.py (excerpt)
query = self._construct_search_query(clause)
retrieved_evidence = self.vector_store.search_documents(query=query, document_id=document_id, top_k=top_k)
llm_evaluation = self._evaluate_with_llm(clause, retrieved_evidence)
rule_results = self.rule_validator.validate_rules(rules=clause.validation_rules, evidence=retrieved_evidence)
final_status, final_confidence, override_applied, override_reason = self._make_final_decision(llm_evaluation, rule_results, clause)
```

### ReportDetail threshold

```javascript
// ReportDetail.jsx
const CONFIDENCE_THRESHOLD = 0.7
const isAmbiguous = (e) => {
  if (e.override_applied) return false
  const status = e.final_status
  const conf = e.final_confidence ?? 0
  return status === 'partial' || conf < CONFIDENCE_THRESHOLD
}
```

### Full prompts

Copy from `backend/app/compliance_pipeline.py` (`TCFD_CHECKER_SYSTEM_PROMPT` through `_get_sasb_prompt` and reflection functions).

### Parser

`backend/app/clause_parser_enhanced.py` — `parse_framework`, GRI scope filter, SASB filter, regex builders per framework.

---

## Completeness note

This document covers **architecture, config values, retrieval math, API surface, major prompts’ location, frontend behavior, and framework behavior** as implemented in the repository. It does **not** include every line of every file, full historical chat logs, or runtime data after reports are cleared/regenerated. For a byte-for-byte archive, zip the repo and preserve `data/chroma_db` and `data/*.json` together.
