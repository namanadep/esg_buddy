"""
Generate BRSR ground truth JSON (top-30 clauses, LLM labels) for any compliance report
evaluated against the BRSR framework.

Writes: Company Reports/BRSR Ground Truth/{Company} Ground Truth.json
Entry shape: clause_id, compliance_status, comments
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.models import ComplianceReport, ESGFramework
from app.brsr_clause_ranking import (
    DEFAULT_BRSR_GROUND_TRUTH_SAMPLE,
    select_top_k_brsr_clauses,
    sort_brsr_clause_ids,
)

logger = logging.getLogger(__name__)

BRSR_GT_SYSTEM = (
    "You are BRSR-Checker, an expert SEBI BRSR auditor. Label one disclosure requirement at a "
    "time using only the report text provided. Output valid JSON only. "
    "Compliant = disclosure fully meets the specific requirement; "
    "Partial = incomplete, high-level, or missing key elements; "
    "Non-Compliant = not evidenced in the excerpt."
)


def brsr_company_from_filename(filename: str) -> Optional[str]:
    u = (filename or "").upper()
    if "SASKEN" in u:
        return "Sasken"
    if "HIMADRI" in u:
        return "Himadri"
    if "NESTLE" in u or "NESTLÉ" in (filename or ""):
        return "Nestle"
    if u.startswith("NYK") or " NYK" in u or "NYK " in u:
        return "NYK"
    if "GIVAUDAN" in u:
        return "Givaudan"
    if "UNILEVER" in u:
        return "Unilever"
    if "GPM" in u:
        return "GPM"
    if "AMAZON" in u:
        return "Amazon"
    if "APPLE" in u:
        return "Apple"
    if "INFOSYS" in u:
        return "Infosys"
    if "TCS" in u:
        return "TCS"
    if "RIL" in u or "RELIANCE" in u:
        return "RIL"
    if "TATA" in u:
        return "TATA Motors"
    return None


def extract_pdf_text(pdf_path: Path) -> str:
    import fitz
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def _evidence_from_evaluation(ev: Optional[Dict[str, Any]]) -> str:
    if not ev:
        return ""
    chunks = ev.get("retrieved_evidence") or []
    return "\n\n".join(c.get("text", "") for c in chunks[:10])[:16000]


def _clause_from_evaluation(ev: dict) -> dict:
    c = ev.get("clause") or {}
    cid = ev.get("clause_id") or c.get("clause_id") or ""
    return {
        "clause_id": cid,
        "title": c.get("title") or cid,
        "description": c.get("description") or "",
        "keywords": c.get("keywords") or [],
    }


def analyze_brsr_clause(
    client: Any,
    pdf_text: str,
    clause: dict,
    company_name: str,
    evidence_fallback: str = "",
    model: Optional[str] = None,
) -> dict:
    title = clause.get("title", "")
    desc = (clause.get("description") or "")[:4000]
    clause_id = clause.get("clause_id", "")

    base = (pdf_text or "").strip()
    if len(base) < 200 and evidence_fallback:
        base = evidence_fallback

    keywords = clause.get("keywords") or []
    excerpt = base[:14000]
    if keywords and base:
        lines = base.split("\n")
        hits = []
        for i, line in enumerate(lines):
            if any(kw.lower() in line.lower() for kw in keywords[:12]):
                start = max(0, i - 8)
                end = min(len(lines), i + 8)
                hits.extend(lines[start:end])
        if hits:
            excerpt = "\n".join(hits)[:14000]

    prompt = f"""**Company / report:** {company_name}

**BRSR clause:** {clause_id}
**Title:** {title}
**Requirement (excerpt):** {desc}

**Report text (excerpt):**
{excerpt}

Classify whether this BRSR disclosure requirement is met in the report excerpt. Use ONLY one of:
- **Compliant** — clear, substantive disclosure addressing the specific requirement.
- **Partial** — mentioned but incomplete, high-level only, or missing key elements.
- **Non-Compliant** — not addressed or no usable evidence in the excerpt.

Respond with JSON only:
{{
  "compliance_status": "Compliant" | "Partial" | "Non-Compliant",
  "comments": "one short sentence"
}}
"""

    model = model or os.getenv("BRSR_GT_LLM_MODEL") or "gpt-4o-mini"
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": BRSR_GT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "compliance_status": "Non-Compliant",
            "comments": f"LLM error: {e}",
        }


def _resolve_clause(
    clause_id: str,
    evaluations: List[dict],
    clause_resolver: Optional[Callable[[str], Optional[dict]]],
) -> Optional[dict]:
    if clause_resolver:
        got = clause_resolver(clause_id)
        if got:
            return got
    ev = next((e for e in evaluations if e.get("clause_id") == clause_id), None)
    if ev:
        return _clause_from_evaluation(ev)
    return None


def generate_brsr_ground_truth_for_report(
    report: ComplianceReport,
    *,
    upload_dir: Path,
    project_root: Path,
    openai_api_key: str,
    clause_resolver: Optional[Callable[[str], Optional[dict]]] = None,
    llm_model: Optional[str] = None,
    max_clauses: Optional[int] = None,
) -> Optional[Path]:
    """
    Write ``Company Reports/BRSR Ground Truth/{Company} Ground Truth.json``.

    max_clauses: None → DEFAULT (30); 0 → all clause IDs (ranked).
    """
    if report.framework != ESGFramework.BRSR:
        logger.debug("Skip BRSR ground truth: report is not BRSR")
        return None

    filename = report.document_metadata.filename or ""
    company = brsr_company_from_filename(filename)
    if not company:
        logger.info("Skip BRSR ground truth: could not infer company from: %s", filename)
        return None

    report_d = report.model_dump(mode="json")
    evaluations = report_d.get("evaluations") or []
    raw_ids = list(dict.fromkeys(e["clause_id"] for e in evaluations if e.get("clause_id")))
    if not raw_ids:
        logger.warning("BRSR ground truth: no clause ids in report %s", report.report_id)
        return None

    k = DEFAULT_BRSR_GROUND_TRUTH_SAMPLE if max_clauses is None else max_clauses
    if k == 0:
        raw_ids = sort_brsr_clause_ids(raw_ids)
        logger.info("BRSR ground truth: using all %s clauses (ranked)", len(raw_ids))
    else:
        raw_ids = select_top_k_brsr_clauses(raw_ids, k)
        logger.info("BRSR ground truth: sampled %s clauses (cap=%s)", len(raw_ids), k)

    pdf_path = Path(upload_dir) / filename
    if pdf_path.exists():
        logger.info("BRSR ground truth: extracting PDF text from %s", pdf_path)
        pdf_text = extract_pdf_text(pdf_path)
    else:
        logger.warning(
            "BRSR ground truth: PDF not at %s; using retrieved evidence per clause only",
            pdf_path,
        )
        pdf_text = ""

    from openai import OpenAI
    client = OpenAI(api_key=openai_api_key)
    out_rows: List[dict] = []
    for i, clause_id in enumerate(raw_ids):
        clause = _resolve_clause(clause_id, evaluations, clause_resolver)
        if not clause:
            continue
        ev_row = next((e for e in evaluations if e.get("clause_id") == clause_id), None)
        evidence_fb = _evidence_from_evaluation(ev_row)
        result = analyze_brsr_clause(
            client,
            pdf_text,
            clause,
            company,
            evidence_fallback=evidence_fb,
            model=llm_model,
        )
        status = result.get("compliance_status", "Non-Compliant")
        if status not in ("Compliant", "Partial", "Non-Compliant"):
            status = "Non-Compliant"
        out_rows.append({
            "clause_id": clause_id,
            "compliance_status": status,
            "comments": result.get("comments", ""),
        })
        if (i + 1) % 10 == 0:
            logger.info("BRSR ground truth: labeled %s / %s clauses", i + 1, len(raw_ids))

    out_dir = project_root / "Company Reports" / "BRSR Ground Truth"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{company} Ground Truth.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_rows, f, indent=2, ensure_ascii=False)

    logger.info(
        "Wrote %s BRSR ground truth labels to %s (report %s)",
        len(out_rows),
        out_path,
        report.report_id,
    )
    return out_path
