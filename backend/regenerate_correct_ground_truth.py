"""
Regenerate BRSR ground truth JSONs for TCS, RIL, and TATA Motors.

- Uses the EXACT clause_id list from your largest saved BRSR compliance report (fixes
  ground_truth_loaded = 0 when old GT files used different IDs than current reports).
- Labels: Compliant | Partial | Non-Compliant only (no Inferred — aligns with app removal
  of inferred; anything the model marks Inferred is saved as Partial).

Run from project root OR from backend/:
  cd backend && python regenerate_correct_ground_truth.py

Requires: OPENAI_API_KEY, PyMuPDF (fitz), PDFs for each company.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

# backend/ directory
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
REPORTS_FILE = BACKEND_DIR / "data" / "compliance_reports.json"
GT_DIR = PROJECT_ROOT / "Company Reports" / "BRSR Ground Truth"

COMPANY_PDF_CANDIDATES = {
    "TCS": [
        PROJECT_ROOT / "Company Reports" / "TCS BRSR.pdf",
        BACKEND_DIR / "data" / "uploads" / "TCS BRSR.pdf",
    ],
    "RIL": [
        PROJECT_ROOT / "Company Reports" / "RIL BRSR.pdf",
        BACKEND_DIR / "data" / "uploads" / "RIL BRSR.pdf",
    ],
    "TATA Motors": [
        PROJECT_ROOT / "Company Reports" / "TATA Motors BRSR.pdf",
        BACKEND_DIR / "data" / "uploads" / "TATA Motors BRSR.pdf",
    ],
}

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(PROJECT_ROOT / "backend" / ".env")
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not set (.env in backend/)")
    sys.exit(1)
client = OpenAI(api_key=api_key)


def normalize_compliance_status(raw: str) -> str:
    """Map model output to loader-expected labels (no Inferred)."""
    s = (raw or "").strip().lower().replace("_", "-")
    if s in ("inferred", "infer"):
        return "Partial"
    if s in ("compliant", "yes", "supported"):
        return "Compliant"
    if s in ("partial", "partially compliant"):
        return "Partial"
    if s in ("non-compliant", "non compliant", "not compliant", "not-supported", "not_supported"):
        return "Non-Compliant"
    return "Non-Compliant"


def resolve_pdf(company: str) -> Optional[Path]:
    for p in COMPANY_PDF_CANDIDATES.get(company, []):
        if p.exists():
            return p
    return None


def get_system_clause_ids() -> list:
    """
    Prefer clause order from the BRSR report with the most evaluations (matches UI reports).
    """
    if not REPORTS_FILE.exists():
        print(f"ERROR: {REPORTS_FILE} not found. Run a BRSR evaluation first.")
        return []

    with open(REPORTS_FILE, "r", encoding="utf-8") as f:
        reports = json.load(f)

    best_ids: list = []
    best_name = None
    for _rid, rep in reports.items():
        if rep.get("framework") != "BRSR":
            continue
        ev = rep.get("evaluations") or []
        ids = [
            e["clause_id"]
            for e in ev
            if isinstance(e, dict) and str(e.get("clause_id", "")).startswith("BRSR")
        ]
        if len(ids) > len(best_ids):
            best_ids = ids
            best_name = (rep.get("document_metadata") or {}).get("filename")

    if best_ids:
        print(f"Using {len(best_ids)} BRSR clause IDs from report: {best_name or '(unknown)'}")
        return best_ids

    print("ERROR: No BRSR report found in compliance_reports.json")
    return []


def extract_pdf_text(pdf_path: Path) -> str:
    import fitz

    doc = fitz.open(pdf_path)
    parts = []
    for page in doc:
        parts.append(page.get_text())
    doc.close()
    return "\n".join(parts)


def analyze_clauses_batch(pdf_text: str, clause_ids: list, company_name: str) -> dict:
    batch_size = 25
    results = {}
    # More context for Annexure sections (still one excerpt; extend size)
    excerpt = pdf_text[:120000] if len(pdf_text) > 120000 else pdf_text

    for i in range(0, len(clause_ids), batch_size):
        batch = clause_ids[i : i + batch_size]
        batch_str = "\n".join(f"- {cid}" for cid in batch)

        prompt = f"""Analyze this {company_name} BRSR report and determine compliance status for each clause below.

**BRSR Report Text (excerpt):**
{excerpt}

**Clauses to evaluate ({len(batch)}):**
{batch_str}

**Use exactly THREE labels only (do not use "Inferred" or any other label):**
- **Compliant**: Disclosure clearly present (data, table, narrative, cross-reference, or "0"/"Nil"/"NA" with reason).
- **Partial**: Some relevant disclosure but incomplete, indirect, implied only, or missing a key part of the requirement.
- **Non-Compliant**: No disclosure or no reasonable proxy.

Return a JSON object with a single key "entries" whose value is an array of objects, each with:
- "clause_id": exact ID from the list above
- "compliance_status": "Compliant" | "Partial" | "Non-Compliant"
- "comments": one short sentence

Use **Partial** where disclosure is weak, indirect, or incomplete (do not use any other label)."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert BRSR analyst. Return ONLY valid JSON with an object containing an 'entries' array.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            entries = result.get("entries", [])
            if not entries and isinstance(result, dict):
                for _k, v in result.items():
                    if isinstance(v, list):
                        entries = v
                        break

            for entry in entries:
                cid = entry.get("clause_id", "")
                if cid in batch:
                    status = normalize_compliance_status(entry.get("compliance_status", ""))
                    # Display format expected by ground_truth_loader (title case Partial/Compliant/Non-Compliant)
                    display = (
                        "Compliant"
                        if status == "Compliant"
                        else ("Partial" if status == "Partial" else "Non-Compliant")
                    )
                    results[cid] = {
                        "compliance_status": display,
                        "comments": entry.get("comments", "") or "",
                    }

            print(f"  Batch {i // batch_size + 1}: got {len(entries)} rows for {len(batch)} clauses")
        except Exception as e:
            print(f"  ERROR in batch {i // batch_size + 1}: {e}")
            for cid in batch:
                results[cid] = {
                    "compliance_status": "Non-Compliant",
                    "comments": f"Analysis error: {e}",
                }

    return results


def generate_ground_truth(company_name: str, clause_ids: list) -> None:
    pdf_path = resolve_pdf(company_name)
    if not pdf_path:
        print(f"ERROR: No PDF found for {company_name}. Tried:")
        for p in COMPANY_PDF_CANDIDATES.get(company_name, []):
            print(f"  - {p}")
        return

    print(f"\nProcessing: {company_name}")
    print(f"PDF: {pdf_path}")
    print(f"Clauses: {len(clause_ids)}")

    print("Extracting PDF text...")
    pdf_text = extract_pdf_text(pdf_path)
    print(f"Extracted {len(pdf_text)} characters")

    print("Analyzing with OpenAI (this may take several minutes)...")
    results = analyze_clauses_batch(pdf_text, clause_ids, company_name)

    ground_truth = []
    for cid in clause_ids:
        entry = results.get(
            cid,
            {"compliance_status": "Non-Compliant", "comments": "Not analyzed"},
        )
        st = normalize_compliance_status(entry["compliance_status"])
        ground_truth.append(
            {
                "clause_id": cid,
                "compliance_status": st,
                "comments": entry.get("comments", "") or "",
            }
        )

    GT_DIR.mkdir(parents=True, exist_ok=True)
    out_name = (
        "TATA Motors Ground Truth.json"
        if company_name == "TATA Motors"
        else f"{company_name} Ground Truth.json"
    )
    output_file = GT_DIR / out_name
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    counts = {}
    for row in ground_truth:
        counts[row["compliance_status"]] = counts.get(row["compliance_status"], 0) + 1
    print(f"Saved: {output_file}")
    print(f"Summary: {counts}")


def main():
    print("Regenerating BRSR Ground Truth (no Inferred; IDs match current reports)")
    print("=" * 60)

    clause_ids = get_system_clause_ids()
    if not clause_ids:
        sys.exit(1)

    print("First clause_ids:", ", ".join(clause_ids[:5]), "...")

    for company in ["TCS", "RIL", "TATA Motors"]:
        try:
            generate_ground_truth(company, clause_ids)
        except Exception as e:
            print(f"ERROR {company}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Done. Restart the backend and open a BRSR report for TCS / RIL / TATA Motors.")
    print("Accuracy uses Compliant~supported, Partial~partial, Non-Compliant~not_supported.")


if __name__ == "__main__":
    main()
