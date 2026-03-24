"""
Generate GRI ground truth JSON (sampled clauses + LLM labels) for a compliance report.

Used by the CLI (generate_gri_ground_truth.py) and automatically after GRI evaluation when enabled.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.gri_clause_ranking import (
    DEFAULT_GRI_GROUND_TRUTH_SAMPLE,
    _is_gri_style_clause_id,
    select_top_k_gri_clauses,
)
from app.models import ComplianceReport, ESGFramework

logger = logging.getLogger(__name__)


def company_from_filename(filename: str) -> Optional[str]:
    u = filename.upper()
    if "GIVAUDAN" in u:
        return "Givaudan"
    if "UNILEVER" in u:
        return "Unilever"
    if "GPM" in u:
        return "GPM"
    if "TCS" in u:
        return "TCS"
    if "RIL" in u or "RELIANCE" in u:
        return "RIL"
    if "TATA" in u:
        return "TATA Motors"
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


def analyze_gri_clause(
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
    excerpt = base[:12000]
    if keywords and base:
        lines = base.split("\n")
        hits = []
        for i, line in enumerate(lines):
            if any(kw.lower() in line.lower() for kw in keywords[:12]):
                start = max(0, i - 8)
                end = min(len(lines), i + 8)
                hits.extend(lines[start:end])
        if hits:
            excerpt = "\n".join(hits)[:12000]

    prompt = f"""You are an expert GRI sustainability report analyst.

**Company / report context:** {company_name}

**GRI clause:** {clause_id}
**Title:** {title}
**Requirement (excerpt):** {desc}

**Report text (excerpt):**
{excerpt}

Classify whether this GRI disclosure requirement is met in the report. Use ONLY one of:
- **Compliant** — clear, substantive disclosure addressing the requirement (supported).
- **Partial** — indirect, incomplete, or only partial coverage.
- **Non-Compliant** — not addressed or no usable evidence.

Respond with JSON only:
{{
  "compliance_status": "Compliant" | "Partial" | "Non-Compliant",
  "comments": "one short sentence"
}}
"""

    model = model or os.getenv("GRI_GT_LLM_MODEL", "gpt-4o-mini")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You classify GRI report disclosures objectively. Output valid JSON only.",
                },
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


def generate_gri_ground_truth_for_report(
    report: ComplianceReport,
    *,
    upload_dir: Path,
    project_root: Path,
    openai_api_key: str,
    clause_resolver: Optional[Callable[[str], Optional[dict]]] = None,
    llm_model: Optional[str] = None,
) -> Optional[Path]:
    """
    Write ``Company Reports/GRI Ground Truth/{Company} GRI Ground Truth.json`` for this report.

    Returns output path, or None if skipped / failed without raising.
    """
    if report.framework != ESGFramework.GRI:
        logger.debug("Skip GRI ground truth: report is not GRI")
        return None

    filename = report.document_metadata.filename or ""
    company = company_from_filename(filename)
    if not company:
        logger.info(
            "Skip auto GRI ground truth: could not infer company from filename: %s", filename
        )
        return None

    report_d = report.model_dump(mode="json")
    evaluations = report_d.get("evaluations") or []
    raw_ids = list(
        dict.fromkeys(e["clause_id"] for e in evaluations if e.get("clause_id"))
    )
    if not raw_ids:
        logger.warning("GRI ground truth: no clause ids in report %s", report.report_id)
        return None

    preferred = [c for c in raw_ids if _is_gri_style_clause_id(c)]
    pool = preferred if len(preferred) >= DEFAULT_GRI_GROUND_TRUTH_SAMPLE else raw_ids
    top_ids = select_top_k_gri_clauses(pool, DEFAULT_GRI_GROUND_TRUTH_SAMPLE)

    pdf_path = Path(upload_dir) / filename
    if pdf_path.exists():
        logger.info("GRI ground truth: extracting PDF text from %s", pdf_path)
        pdf_text = extract_pdf_text(pdf_path)
    else:
        logger.warning(
            "GRI ground truth: PDF not at %s; using retrieved evidence per clause only",
            pdf_path,
        )
        pdf_text = ""

    from openai import OpenAI

    client = OpenAI(api_key=openai_api_key)
    out_rows: List[dict] = []
    for clause_id in top_ids:
        clause = _resolve_clause(clause_id, evaluations, clause_resolver)
        if not clause:
            continue
        ev_row = next((e for e in evaluations if e.get("clause_id") == clause_id), None)
        evidence_fb = _evidence_from_evaluation(ev_row)
        result = analyze_gri_clause(
            client,
            pdf_text,
            clause,
            company,
            evidence_fallback=evidence_fb,
            model=llm_model or os.getenv("GRI_GT_LLM_MODEL"),
        )
        status = result.get("compliance_status", "Non-Compliant")
        if status not in ("Compliant", "Partial", "Non-Compliant"):
            status = "Non-Compliant"
        out_rows.append(
            {
                "clause_id": clause_id,
                "title": clause.get("title"),
                "compliance_status": status,
                "comments": result.get("comments", ""),
            }
        )

    out_dir = project_root / "Company Reports" / "GRI Ground Truth"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{company} GRI Ground Truth.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_rows, f, indent=2, ensure_ascii=False)

    logger.info(
        "Wrote %s GRI ground truth labels to %s (report %s)",
        len(out_rows),
        out_path,
        report.report_id,
    )
    return out_path


def run_auto_gri_ground_truth_after_evaluation(
    report: ComplianceReport,
    *,
    upload_dir: Path,
    project_root: Path,
    openai_api_key: str,
    clause_resolver: Optional[Callable[[str], Optional[dict]]] = None,
    llm_model: Optional[str] = None,
) -> None:
    """Background task entry point: log errors, never raise to client."""
    try:
        generate_gri_ground_truth_for_report(
            report,
            upload_dir=upload_dir,
            project_root=project_root,
            openai_api_key=openai_api_key,
            clause_resolver=clause_resolver,
            llm_model=llm_model,
        )
    except Exception:
        logger.exception(
            "Auto GRI ground truth generation failed for report %s", report.report_id
        )
