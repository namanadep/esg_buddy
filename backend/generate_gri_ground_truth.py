"""
CLI wrapper for GRI ground truth generation (same logic as auto-run after /compliance/evaluate).

Usage:
  cd backend
  python generate_gri_ground_truth.py --report-id <id> --compliance-json data/compliance_reports.json
  python generate_gri_ground_truth.py --report-id <id> --compliance-json data/compliance_reports.json --pdf "C:/path/Unilever GRI.pdf"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")
load_dotenv(BACKEND_ROOT.parent / ".env")

from app.config import settings  # noqa: E402
from app.gri_ground_truth_generator import (  # noqa: E402
    _clause_from_evaluation,
    company_from_filename,
    generate_gri_ground_truth_for_report,
)
from app.models import ComplianceReport  # noqa: E402

API_BASE = os.getenv("ESGBUDDY_API_BASE", "http://127.0.0.1:8000")


def _fetch_clause_api(clause_id: str) -> dict | None:
    try:
        cr = requests.get(f"{API_BASE}/clauses/{clause_id}", timeout=60)
        if cr.status_code == 200:
            return cr.json()
    except requests.RequestException:
        pass
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate GRI ground truth JSON for a report")
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--compliance-json", type=Path, default=None)
    parser.add_argument("--pdf", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.compliance_json:
        with open(args.compliance_json, "r", encoding="utf-8") as f:
            all_reports = json.load(f)
        raw = all_reports.get(args.report_id)
        if not raw:
            print("ERROR: report_id not in JSON")
            sys.exit(1)
        report = ComplianceReport.model_validate(raw)
    else:
        r = requests.get(f"{API_BASE}/compliance/reports/{args.report_id}", timeout=120)
        r.raise_for_status()
        report = ComplianceReport.model_validate(r.json())

    if report.framework.value != "GRI":
        print("ERROR: Report is not GRI")
        sys.exit(1)

    filename = report.document_metadata.filename or ""
    if not company_from_filename(filename):
        print("ERROR: Could not infer company from filename:", filename)
        sys.exit(1)

    if args.dry_run:
        from app.gri_clause_ranking import (
            DEFAULT_GRI_GROUND_TRUTH_SAMPLE,
            _is_gri_style_clause_id,
            select_top_k_gri_clauses,
        )

        evs = report.model_dump(mode="json").get("evaluations") or []
        raw_ids = list(dict.fromkeys(e["clause_id"] for e in evs if e.get("clause_id")))
        preferred = [c for c in raw_ids if _is_gri_style_clause_id(c)]
        pool = preferred if len(preferred) >= DEFAULT_GRI_GROUND_TRUTH_SAMPLE else raw_ids
        top_ids = select_top_k_gri_clauses(pool, DEFAULT_GRI_GROUND_TRUTH_SAMPLE)
        print(f"Selected {len(top_ids)} GRI clauses (dry-run)")
        for cid in top_ids:
            print(" ", cid)
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set")
        sys.exit(1)

    project_root = BACKEND_ROOT.parent
    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.is_file():
            print("ERROR: --pdf not found:", pdf_path)
            sys.exit(1)
        upload_dir = pdf_path.resolve().parent
    else:
        upload_dir = Path(settings.upload_dir)
        if not upload_dir.is_absolute():
            upload_dir = (BACKEND_ROOT / upload_dir).resolve()

    evaluations = report.model_dump(mode="json").get("evaluations") or []

    def clause_resolver(cid: str):
        got = _fetch_clause_api(cid)
        if got:
            return got
        ev = next((e for e in evaluations if e.get("clause_id") == cid), None)
        return _clause_from_evaluation(ev) if ev else None

    generate_gri_ground_truth_for_report(
        report,
        upload_dir=upload_dir,
        project_root=project_root,
        openai_api_key=api_key,
        clause_resolver=clause_resolver,
        llm_model=os.getenv("GRI_GT_LLM_MODEL") or settings.llm_model,
    )
    print("Done.")


if __name__ == "__main__":
    main()
