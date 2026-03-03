"""
Regenerate ground truth files using the ACTUAL clause IDs from the system's reports.

The system uses clause IDs like BRSR-Core-GHG-Scope1-TotalEmissions (hyphenated, semantic)
NOT BRSR_Core_1_Green-house_gas_GHG_footprint (from clause_parser_enhanced.py).

This script extracts the actual clause IDs from existing compliance reports
and creates ground truth templates that match them exactly.
"""

import json
import os
import re
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

COMPANY_PDFS = {
    "TCS": "Company Reports/TCS BRSR.pdf",
    "RIL": "Company Reports/RIL BRSR.pdf",
    "TATA Motors": "Company Reports/TATA Motors BRSR.pdf"
}

def get_system_clause_ids():
    """Extract actual BRSR clause IDs from existing compliance reports"""
    reports_file = Path("backend/data/compliance_reports.json")
    
    if not reports_file.exists():
        print("ERROR: compliance_reports.json not found")
        return []
    
    with open(reports_file, 'r', encoding='utf-8') as f:
        data = f.read()
    
    # Extract all clause IDs used in BRSR reports
    ids = re.findall(r'"clause_id": "([^"]+)"', data)
    unique = sorted(set(ids))
    
    # Filter to only BRSR clause IDs
    brsr_ids = [x for x in unique if x.startswith('BRSR')]
    
    print(f"Found {len(brsr_ids)} unique BRSR clause IDs in existing reports")
    return brsr_ids

def extract_pdf_text(pdf_path):
    """Extract text from PDF"""
    import fitz
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def analyze_clauses_batch(pdf_text, clause_ids, company_name):
    """Use AI to analyze compliance for a batch of clauses"""
    
    # Send batches of clause IDs to AI for efficiency
    batch_size = 30
    results = {}
    
    for i in range(0, len(clause_ids), batch_size):
        batch = clause_ids[i:i+batch_size]
        batch_str = "\n".join([f"- {cid}" for cid in batch])
        
        # Use relevant text sections
        # For BRSR Core, look for sections with relevant keywords
        relevant_text = pdf_text[:30000]  # First 30K chars usually contain BRSR Core
        
        prompt = f"""Analyze this {company_name} BRSR report and determine compliance status for each clause below.

**BRSR Report Text (excerpt):**
{relevant_text}

**Clauses to evaluate ({len(batch)}):**
{batch_str}

**Classification Rules:**
- "Compliant": Data/disclosure explicitly present (numbers, tables, narratives, "0", "Nil", "NA" with reason)
- "Partial": Some data present but key elements missing
- "Inferred": Can be reasonably inferred from other disclosures
- "Non-Compliant": No disclosure, no explanation, field blank

**Respond with a JSON array. Each entry must have:**
- clause_id: exact ID from the list above
- compliance_status: "Compliant" | "Partial" | "Inferred" | "Non-Compliant"
- comments: brief explanation (1 sentence)

**Respond with ONLY the JSON array, nothing else.**"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert BRSR compliance analyst. Return ONLY valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Handle both {results: [...]} and [...] formats
            if isinstance(result, dict):
                entries = result.get("results", result.get("clauses", result.get("data", [])))
                if not entries:
                    for key in result:
                        if isinstance(result[key], list):
                            entries = result[key]
                            break
            else:
                entries = result
            
            for entry in entries:
                cid = entry.get("clause_id", "")
                if cid in batch:
                    results[cid] = {
                        "compliance_status": entry.get("compliance_status", "Non-Compliant"),
                        "comments": entry.get("comments", "")
                    }
            
            print(f"  Batch {i//batch_size + 1}: analyzed {len(entries)} clauses")
            
        except Exception as e:
            print(f"  ERROR in batch {i//batch_size + 1}: {e}")
            for cid in batch:
                results[cid] = {
                    "compliance_status": "Non-Compliant",
                    "comments": f"Analysis error: {e}"
                }
    
    return results

def generate_ground_truth(company_name, clause_ids):
    """Generate ground truth for one company"""
    pdf_path = COMPANY_PDFS.get(company_name)
    if not pdf_path or not Path(pdf_path).exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return
    
    print(f"\nProcessing: {company_name}")
    print(f"PDF: {pdf_path}")
    print(f"Clauses to evaluate: {len(clause_ids)}")
    
    # Extract PDF text
    print("Extracting PDF text...")
    pdf_text = extract_pdf_text(pdf_path)
    print(f"Extracted {len(pdf_text)} characters")
    
    # Analyze with AI
    print("Analyzing with AI...")
    results = analyze_clauses_batch(pdf_text, clause_ids, company_name)
    
    # Build ground truth JSON
    ground_truth = []
    for cid in clause_ids:
        entry = results.get(cid, {"compliance_status": "Non-Compliant", "comments": "Not analyzed"})
        ground_truth.append({
            "clause_id": cid,
            "compliance_status": entry["compliance_status"],
            "comments": entry["comments"]
        })
    
    # Save
    output_file = Path(f"Company Reports/BRSR Ground Truth/{company_name} Ground Truth.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)
    
    # Summary
    statuses = {}
    for entry in ground_truth:
        s = entry["compliance_status"]
        statuses[s] = statuses.get(s, 0) + 1
    
    print(f"Saved: {output_file}")
    print(f"Summary: {statuses}")

def main():
    print("Regenerating Ground Truth with CORRECT Clause IDs")
    print("="*60)
    
    # Get actual system clause IDs
    clause_ids = get_system_clause_ids()
    if not clause_ids:
        print("No clause IDs found!")
        return
    
    print(f"\nSample IDs:")
    for cid in clause_ids[:5]:
        print(f"  {cid}")
    print(f"  ... ({len(clause_ids)} total)")
    
    # Generate for each company
    for company in ["TCS", "RIL", "TATA Motors"]:
        try:
            generate_ground_truth(company, clause_ids)
        except Exception as e:
            print(f"ERROR: {company}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("Done! Ground truth files regenerated with correct clause IDs.")
    print("Restart backend and generate a new report to see accuracy metrics.")

if __name__ == "__main__":
    main()
