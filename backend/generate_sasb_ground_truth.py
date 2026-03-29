"""
Generate SASB ground truth JSON for a compliance report (LLM labels per clause).

Usage:
  cd backend
  python generate_sasb_ground_truth.py --report-id <id> --compliance-json data/compliance_reports.json
  python generate_sasb_ground_truth.py --batch-sasb --compliance-json data/compliance_reports.json
  # Default: top 30 ranked clauses per report. Full report: add --all-clauses
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
from app.models import ComplianceReport, ESGFramework  # noqa: E402
from app.gri_ground_truth_generator import _clause_from_evaluation  # noqa: E402
from app.sasb_ground_truth_generator import (  # noqa: E402
    generate_sasb_ground_truth_for_report,
    sasb_company_from_filename,
)

API_BASE = os.getenv("ESGBUDDY_API_BASE", "http://127.0.0.1:8000")


def _fetch_clause_api(clause_id: str) -> dict | None:
    try:
        cr = requests.get(f"{API_BASE}/clauses/{clause_id}", timeout=60)
        if cr.status_code == 200:
            return cr.json()
    except requests.RequestException:
        pass
    return None


def _run_one_report(
    report: ComplianceReport,
    *,
    upload_dir: Path,
    project_root: Path,
    api_key: str,
    max_clauses: int | None,
) -> None:
    evaluations = report.model_dump(mode="json").get("evaluations") or []

    def clause_resolver(cid: str):
        got = _fetch_clause_api(cid)
        if got:
            return got
        ev = next((e for e in evaluations if e.get("clause_id") == cid), None)
        return _clause_from_evaluation(ev) if ev else None

    generate_sasb_ground_truth_for_report(
        report,
        upload_dir=upload_dir,
        project_root=project_root,
        openai_api_key=api_key,
        clause_resolver=clause_resolver,
        llm_model=os.getenv("SASB_GT_LLM_MODEL") or settings.llm_model,
        max_clauses=max_clauses,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SASB ground truth JSON for report(s)")
    parser.add_argument("--report-id", default=None, help="Single compliance report id")
    parser.add_argument(
        "--compliance-json",
        type=Path,
        default=BACKEND_ROOT / "data" / "compliance_reports.json",
    )
    parser.add_argument(
        "--max-clauses",
        type=int,
        default=30,
        help="Top N ranked SASB clauses to label (default: 30). Use with --all-clauses for full report.",
    )
    parser.add_argument(
        "--all-clauses",
        action="store_true",
        help="Label every clause in the report (ranked order; many LLM calls).",
    )
    parser.add_argument(
        "--batch-sasb",
        action="store_true",
        help="Process all SASB reports for Amazon, Apple, Infosys found in compliance JSON",
    )
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set")
        sys.exit(1)

    project_root = BACKEND_ROOT.parent
    upload_dir = Path(settings.upload_dir)
    if not upload_dir.is_absolute():
        upload_dir = (BACKEND_ROOT / upload_dir).resolve()

    if not args.compliance_json.is_file():
        print("ERROR: compliance JSON not found:", args.compliance_json)
        sys.exit(1)

    with open(args.compliance_json, "r", encoding="utf-8") as f:
        all_reports = json.load(f)

    to_run: list[ComplianceReport] = []

    if args.batch_sasb:
        by_company: dict[str, ComplianceReport] = {}
        for rid, raw in all_reports.items():
            try:
                rep = ComplianceReport.model_validate(raw)
            except Exception:
                continue
            if rep.framework != ESGFramework.SASB:
                continue
            fn = rep.document_metadata.filename or ""
            comp = sasb_company_from_filename(fn)
            if not comp:
                continue
            prev = by_company.get(comp)
            if prev is None or rep.report_id > prev.report_id:
                by_company[comp] = rep
        to_run = list(by_company.values())
        if not to_run:
            print("ERROR: No SASB reports found for Amazon / Apple / Infosys in JSON")
            sys.exit(1)
        print(f"Batch: {len(to_run)} SASB report(s) (latest per company)")
    else:
        if not args.report_id:
            print("ERROR: pass --report-id or --batch-sasb")
            sys.exit(1)
        raw = all_reports.get(args.report_id)
        if not raw:
            print("ERROR: report_id not in JSON")
            sys.exit(1)
        to_run.append(ComplianceReport.model_validate(raw))

    for report in to_run:
        if report.framework != ESGFramework.SASB:
            print(f"SKIP (not SASB): {report.report_id}")
            continue
        fn = report.document_metadata.filename or ""
        if not sasb_company_from_filename(fn):
            print(f"SKIP (filename not Amazon/Apple/Infosys): {fn!r} {report.report_id}")
            continue
        print(f"Generating SASB ground truth for {fn!r} ({report.report_id}) ...")
        mc = 0 if args.all_clauses else args.max_clauses
        _run_one_report(
            report,
            upload_dir=upload_dir,
            project_root=project_root,
            api_key=api_key,
            max_clauses=mc,
        )

    print("Done.")


if __name__ == "__main__":
    main()
