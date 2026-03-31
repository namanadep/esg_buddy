"""
Generate missing ground truth files for all company × framework combinations.

Run from the project root:
    cd backend && python ../generate_all_ground_truth.py

Uses the existing generators (BRSR/GRI/TCFD/SASB) to label the top 30 clauses
for each report that doesn't already have a GT file.
"""

import sys
import json
import logging
import os
from pathlib import Path

# Add backend/app to path
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

os.environ["ANONYMIZED_TELEMETRY"] = "False"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

from app.models import ComplianceReport, ESGFramework
from app.config import settings
from app.brsr_ground_truth_generator import generate_brsr_ground_truth_for_report, brsr_company_from_filename
from app.gri_ground_truth_generator import generate_gri_ground_truth_for_report, company_from_filename as gri_company_from_filename
from app.tcfd_ground_truth_generator import generate_tcfd_ground_truth_for_report, tcfd_company_from_filename
from app.sasb_ground_truth_generator import generate_sasb_ground_truth_for_report, sasb_company_from_filename
from app.ground_truth_loader import GroundTruthLoader

PROJECT_ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = (PROJECT_ROOT / "backend" / settings.upload_dir).resolve()
REPORTS_FILE = PROJECT_ROOT / "backend" / "data" / "compliance_reports.json"

BRSR_GT_DIR = PROJECT_ROOT / "Company Reports" / "BRSR Ground Truth"
GRI_GT_DIR = PROJECT_ROOT / "Company Reports" / "GRI Ground Truth"
TCFD_GT_DIR = PROJECT_ROOT / "Company Reports" / "TCFD Ground Truth"
SASB_GT_DIR = PROJECT_ROOT / "Company Reports" / "SASB Ground Truth"

loader = GroundTruthLoader()


def gt_file_exists(framework: ESGFramework, company: str) -> bool:
    if framework == ESGFramework.BRSR:
        return (BRSR_GT_DIR / loader.company_mappings.get(company, "__missing__")).exists()
    elif framework == ESGFramework.GRI:
        return (GRI_GT_DIR / loader.gri_company_mappings.get(company, "__missing__")).exists()
    elif framework == ESGFramework.TCFD:
        return (TCFD_GT_DIR / loader.tcfd_company_mappings.get(company, "__missing__")).exists()
    elif framework == ESGFramework.SASB:
        return (SASB_GT_DIR / loader.sasb_company_mappings.get(company, "__missing__")).exists()
    return False


def company_from_filename(filename: str, framework: ESGFramework):
    if framework == ESGFramework.BRSR:
        return brsr_company_from_filename(filename)
    elif framework == ESGFramework.GRI:
        return gri_company_from_filename(filename)
    elif framework == ESGFramework.TCFD:
        return tcfd_company_from_filename(filename)
    elif framework == ESGFramework.SASB:
        return sasb_company_from_filename(filename)
    return None


def main():
    if not REPORTS_FILE.exists():
        logger.error("compliance_reports.json not found at %s", REPORTS_FILE)
        sys.exit(1)

    with open(REPORTS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    reports = {}
    for rid, rdata in raw.items():
        try:
            reports[rid] = ComplianceReport.model_validate(rdata)
        except Exception as e:
            logger.warning("Could not load report %s: %s", rid, e)

    logger.info("Loaded %d reports", len(reports))

    # Deduplicate: one representative report per (company, framework)
    seen = {}
    for rid, report in reports.items():
        filename = report.document_metadata.filename or ""
        fw = report.framework
        company = company_from_filename(filename, fw)
        if not company:
            continue
        key = (company, fw)
        if key not in seen:
            seen[key] = report

    openai_api_key = settings.openai_api_key
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not set in environment / .env")
        sys.exit(1)

    generated = 0
    skipped = 0

    for (company, fw), report in sorted(seen.items(), key=lambda x: (x[0][0], x[0][1].value)):
        if gt_file_exists(fw, company):
            logger.info("SKIP  %-15s %-5s — GT file already exists", company, fw.value)
            skipped += 1
            continue

        logger.info("GEN   %-15s %-5s — generating...", company, fw.value)
        try:
            if fw == ESGFramework.BRSR:
                path = generate_brsr_ground_truth_for_report(
                    report,
                    upload_dir=UPLOAD_DIR,
                    project_root=PROJECT_ROOT,
                    openai_api_key=openai_api_key,
                )
            elif fw == ESGFramework.GRI:
                path = generate_gri_ground_truth_for_report(
                    report,
                    upload_dir=UPLOAD_DIR,
                    project_root=PROJECT_ROOT,
                    openai_api_key=openai_api_key,
                )
            elif fw == ESGFramework.TCFD:
                path = generate_tcfd_ground_truth_for_report(
                    report,
                    upload_dir=UPLOAD_DIR,
                    project_root=PROJECT_ROOT,
                    openai_api_key=openai_api_key,
                )
            elif fw == ESGFramework.SASB:
                path = generate_sasb_ground_truth_for_report(
                    report,
                    upload_dir=UPLOAD_DIR,
                    project_root=PROJECT_ROOT,
                    openai_api_key=openai_api_key,
                )
            else:
                path = None

            if path:
                logger.info("DONE  %-15s %-5s → %s", company, fw.value, path.name)
                generated += 1
            else:
                logger.warning("SKIP  %-15s %-5s — generator returned None", company, fw.value)
        except Exception as e:
            logger.error("ERROR %-15s %-5s — %s", company, fw.value, e)

    logger.info("=== Done: %d generated, %d skipped (already existed) ===", generated, skipped)


if __name__ == "__main__":
    main()
