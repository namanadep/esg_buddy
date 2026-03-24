"""
Run generate_gri_ground_truth.py for Unilever, GPM, and Givaudan (latest GRI report ids in data/compliance_reports.json).

Usage (from backend/):
  python batch_gri_ground_truth.py

Requires OPENAI_API_KEY. PDFs optional if evaluations contain retrieved evidence.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
JSON = BACKEND / "data" / "compliance_reports.json"

# Latest GRI run per company PDF (update if you regenerate reports)
REPORTS = [
    ("Unilever GRI.pdf", "report_ea808a2bded0cc83_GRI_20260323_220859"),
    ("GPM GRI.pdf", "report_cb16e4445fce6615_GRI_20260323_220357"),
    ("Givaudan GRI.pdf", "report_1a6dd3a42e320ffa_GRI_20260323_215340"),
]


def main() -> None:
    if not JSON.is_file():
        print(f"Missing {JSON}")
        sys.exit(1)
    for label, rid in REPORTS:
        print(f"\n=== {label} ({rid}) ===\n", flush=True)
        cmd = [
            sys.executable,
            str(BACKEND / "generate_gri_ground_truth.py"),
            "--report-id",
            rid,
            "--compliance-json",
            str(JSON),
        ]
        subprocess.run(cmd, cwd=str(BACKEND), check=True)
    print("\nDone. Files under Company Reports/GRI Ground Truth/")


if __name__ == "__main__":
    main()
