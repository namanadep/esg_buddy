"""
Generate TCFD ground truth JSON for a compliance report (LLM labels per clause).

Usage:
  cd backend
  python generate_tcfd_ground_truth.py --report-id <id> --compliance-json data/compliance_reports.json
  python generate_tcfd_ground_truth.py --batch-tcfd --compliance-json data/compliance_reports.json
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
from app.tcfd_ground_truth_generator import (  # noqa: E402
    generate_tcfd_ground_truth_for_report,
    tcfd_company_from_filename,
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

    generate_tcfd_ground_truth_for_report(
        report,
        upload_dir=upload_dir,
        project_root=project_root,
        openai_api_key=api_key,
        clause_resolver=clause_resolver,
        llm_model=os.getenv("TCFD_GT_LLM_MODEL") or settings.llm_model,
        max_clauses=max_clauses,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TCFD ground truth JSON for report(s)")
    parser.add_argument("--report-id", default=None, help="Single compliance report id")
    parser.add_argument("--compliance-json", type=Path, default=BACKEND_ROOT / "data" / "compliance_reports.json")
    parser.add_argument(
        "--max-clauses",
        type=int,
        default=30,
        help="Top N ranked TCFD clauses to label (default: 30). Use with --all-clauses for full report.",
    )
    parser.add_argument(
        "--all-clauses",
        action="store_true",
        help="Label every clause in the report (ranked order; many LLM calls).",
    )
    parser.add_argument(
        "--batch-tcfd",
        action="store_true",
        help="Process all TCFD reports for NYK, Himadri, Nestle found in compliance JSON",
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

    if args.batch_tcfd:
        for rid, raw in all_reports.items():
            try:
                rep = ComplianceReport.model_validate(raw)
            except Exception:
                continue
            if rep.framework != ESGFramework.TCFD:
                continue
            fn = rep.document_metadata.filename or ""
            if tcfd_company_from_filename(fn):
                to_run.append(rep)
        if not to_run:
            print("ERROR: No TCFD reports found for NYK / Himadri / Nestle in JSON")
            sys.exit(1)
        print(f"Batch: {len(to_run)} TCFD report(s)")
    else:
        if not args.report_id:
            print("ERROR: pass --report-id or --batch-tcfd")
            sys.exit(1)
        raw = all_reports.get(args.report_id)
        if not raw:
            print("ERROR: report_id not in JSON")
            sys.exit(1)
        to_run.append(ComplianceReport.model_validate(raw))

    for report in to_run:
        if report.framework != ESGFramework.TCFD:
            print(f"SKIP (not TCFD): {report.report_id}")
            continue
        fn = report.document_metadata.filename or ""
        if not tcfd_company_from_filename(fn):
            print(f"SKIP (filename not NYK/Himadri/Nestle): {fn!r} {report.report_id}")
            continue
        print(f"Generating TCFD ground truth for {fn!r} ({report.report_id}) ...")
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
