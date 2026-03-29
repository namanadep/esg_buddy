"""
Generate TCFD ground truth JSON (LLM labels per clause) for compliance reports.

Writes: Company Reports/TCFD Ground Truth/{Company} TCFD Ground Truth.json
Same entry shape as GRI/BRSR: clause_id, compliance_status, comments (optional expected_evidence_pages).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.models import ComplianceReport, ESGFramework
from app.tcfd_clause_ranking import (
    DEFAULT_TCFD_GROUND_TRUTH_SAMPLE,
    select_top_k_tcfd_clauses,
    sort_tcfd_clause_ids,
)

logger = logging.getLogger(__name__)

TCFD_GT_SYSTEM = (
    "You are TCFD-Checker, an expert TCFD auditor. You label one requirement at a time using only "
    "the report text provided. Output valid JSON only. "
    "Compliant = disclosure fully meets the specific requirement; Partial = incomplete or generic; "
    "Non-Compliant = not evidenced in the excerpt."
)


def tcfd_company_from_filename(filename: str) -> Optional[str]:
    u = (filename or "").upper()
    if "HIMADRI" in u:
        return "Himadri"
    if "NESTLE" in u or "NESTLÉ" in (filename or ""):
        return "Nestle"
    if u.startswith("NYK") or " NYK" in u or "NYK " in u:
        return "NYK"
    return None


def extract_pdf_text(pdf_path: Path) -> str:
    import fitz  # PyMuPDF

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


def analyze_tcfd_clause(
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

**TCFD clause ID:** {clause_id}
**Title:** {title}
**Requirement:** {desc}

**Report text (excerpt):**
{excerpt}

Classify whether this specific TCFD-related requirement is met in the report excerpt. Use ONLY one of:
- **Compliant** — substantive disclosure that fully addresses this requirement (specific enough; not generic boilerplate alone).
- **Partial** — mentioned but incomplete, vague, indirect, or missing key elements of this requirement.
- **Non-Compliant** — not addressed or no usable evidence in the excerpt.

Respond with JSON only:
{{
  "compliance_status": "Compliant" | "Partial" | "Non-Compliant",
  "comments": "one short sentence with rationale"
}}
"""

    model = model or os.getenv("TCFD_GT_LLM_MODEL") or os.getenv("GRI_GT_LLM_MODEL") or "gpt-4o-mini"
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": TCFD_GT_SYSTEM},
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


def generate_tcfd_ground_truth_for_report(
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
    Write ``Company Reports/TCFD Ground Truth/{Company} TCFD Ground Truth.json``.

    Clause selection (ranked: pillars Governance→Strategy→Risk→Metrics, then letter/sub-id):
    - ``max_clauses`` is ``None``: use ``DEFAULT_TCFD_GROUND_TRUTH_SAMPLE`` (30).
    - ``max_clauses > 0``: top K after ranking.
    - ``max_clauses == 0``: all clause IDs in the report (full ranked list).
    """
    if report.framework != ESGFramework.TCFD:
        logger.debug("Skip TCFD ground truth: report is not TCFD")
        return None

    filename = report.document_metadata.filename or ""
    company = tcfd_company_from_filename(filename)
    if not company:
        logger.info(
            "Skip TCFD ground truth: could not infer company from filename: %s", filename
        )
        return None

    report_d = report.model_dump(mode="json")
    evaluations = report_d.get("evaluations") or []
    raw_ids = list(dict.fromkeys(e["clause_id"] for e in evaluations if e.get("clause_id")))
    if not raw_ids:
        logger.warning("TCFD ground truth: no clause ids in report %s", report.report_id)
        return None

    k = DEFAULT_TCFD_GROUND_TRUTH_SAMPLE if max_clauses is None else max_clauses
    if k == 0:
        raw_ids = sort_tcfd_clause_ids(raw_ids)
        logger.info("TCFD ground truth: using all %s clauses (ranked)", len(raw_ids))
    else:
        raw_ids = select_top_k_tcfd_clauses(raw_ids, k)
        logger.info(
            "TCFD ground truth: sampled %s / top-ranked clauses (cap=%s)",
            len(raw_ids),
            k,
        )

    pdf_path = Path(upload_dir) / filename
    if pdf_path.exists():
        logger.info("TCFD ground truth: extracting PDF text from %s", pdf_path)
        pdf_text = extract_pdf_text(pdf_path)
    else:
        logger.warning(
            "TCFD ground truth: PDF not at %s; using retrieved evidence per clause only",
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
        result = analyze_tcfd_clause(
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
        row = {
            "clause_id": clause_id,
            "title": clause.get("title"),
            "compliance_status": status,
            "comments": result.get("comments", ""),
        }
        out_rows.append(row)
        if (i + 1) % 20 == 0:
            logger.info("TCFD ground truth: labeled %s / %s clauses", i + 1, len(raw_ids))

    out_dir = project_root / "Company Reports" / "TCFD Ground Truth"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{company} TCFD Ground Truth.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_rows, f, indent=2, ensure_ascii=False)

    logger.info(
        "Wrote %s TCFD ground truth labels to %s (report %s)",
        len(out_rows),
        out_path,
        report.report_id,
    )
    return out_path
