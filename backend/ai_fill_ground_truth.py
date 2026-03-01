"""
AI-Powered Ground Truth Generator

Uses OpenAI to analyze BRSR PDFs and automatically determine compliance status
for each Core metric.

Usage:
    python backend/ai_fill_ground_truth.py
"""

import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

COMPANY_PDFS = {
    "TCS": "Company Reports/TCS BRSR.pdf",
    "RIL": "Company Reports/RIL BRSR.pdf",
    "TATA Motors": "Company Reports/TATA Motors BRSR.pdf"
}

def extract_pdf_text(pdf_path: str) -> str:
    """Extract text from PDF"""
    import fitz  # PyMuPDF
    
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    
    return text

def analyze_clause_compliance(pdf_text: str, clause: dict, company_name: str) -> dict:
    """Use AI to determine if a clause is compliant based on PDF content"""
    
    # Search for relevant section in PDF (BRSR Core table)
    # For efficiency, only send relevant excerpts to AI
    keywords = " ".join(clause.get("keywords", []))
    
    # Find relevant sections (search for keywords in text)
    lines = pdf_text.split('\n')
    relevant_lines = []
    for i, line in enumerate(lines):
        if any(kw.lower() in line.lower() for kw in clause.get("keywords", [])):
            # Get context (10 lines before and after)
            start = max(0, i - 10)
            end = min(len(lines), i + 10)
            relevant_lines.extend(lines[start:end])
    
    relevant_text = '\n'.join(relevant_lines[:5000])  # Limit to 5000 chars
    
    if not relevant_text.strip():
        relevant_text = pdf_text[:10000]  # Fallback to first 10k chars
    
    # AI prompt
    prompt = f"""Analyze this BRSR report excerpt for {company_name} and determine compliance for this Core metric.

**Metric:** {clause['title']}
**Description:** {clause['description']}
**Keywords:** {keywords}

**BRSR Report Excerpt:**
{relevant_text}

**Task:** Determine if this metric is disclosed in the report.

**Classification Rules:**
- **Compliant**: Data is explicitly disclosed (numbers, tables, or clear statements). Includes "0", "Nil", "NA" with reason.
- **Partial**: Some data disclosed but key elements missing (e.g., Scope 1+2 but no Scope 3).
- **Inferred**: Not directly stated but can be reasonably inferred from other disclosures.
- **Non-Compliant**: No disclosure and no explanation.

**Response Format (JSON only):**
{{
    "compliance_status": "Compliant | Partial | Inferred | Non-Compliant",
    "comments": "Brief explanation of what was found or missing",
    "evidence_quote": "Exact quote from report if found (max 200 chars)"
}}

Respond with ONLY the JSON, no other text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert BRSR compliance analyst. Analyze reports accurately and objectively."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"  ERROR analyzing {clause['clause_id']}: {e}")
        return {
            "compliance_status": "TO_REVIEW",
            "comments": f"AI analysis failed: {e}",
            "evidence_quote": ""
        }

def generate_ground_truth_for_company(company_name: str):
    """Generate ground truth for one company"""
    
    pdf_path = COMPANY_PDFS.get(company_name)
    if not pdf_path or not Path(pdf_path).exists():
        print(f"ERROR: PDF not found for {company_name}: {pdf_path}")
        return
    
    print(f"\n{'='*60}")
    print(f"Processing: {company_name}")
    print(f"PDF: {pdf_path}")
    print(f"{'='*60}")
    
    # Extract PDF text
    print("Extracting PDF text...")
    try:
        pdf_text = extract_pdf_text(pdf_path)
        print(f"Extracted {len(pdf_text)} characters")
    except Exception as e:
        print(f"ERROR extracting PDF: {e}")
        return
    
    # Load template
    template_file = Path(f"Company Reports/BRSR Ground Truth/New/{company_name} Ground Truth - Core Only.json")
    with open(template_file, 'r', encoding='utf-8') as f:
        template = json.load(f)
    
    # Process each clause
    ground_truth = []
    
    for entry in template:
        # Skip metadata entries
        if "_comment" in entry or "_instructions" in entry or "_pdf_location" in entry:
            continue
        
        if entry.get("compliance_status") == "TO_REVIEW":
            print(f"\nAnalyzing: {entry['clause_id']}")
            
            # Use AI to analyze
            result = analyze_clause_compliance(pdf_text, entry, company_name)
            
            entry["compliance_status"] = result.get("compliance_status", "TO_REVIEW")
            entry["comments"] = result.get("comments", "")
            
            if result.get("evidence_quote"):
                entry["comments"] += f" | Evidence: {result['evidence_quote']}"
            
            print(f"  Status: {entry['compliance_status']}")
            print(f"  Comments: {entry['comments'][:100]}")
        
        ground_truth.append(entry)
    
    # Save result
    output_file = Path(f"Company Reports/BRSR Ground Truth/{company_name} Ground Truth.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Saved: {output_file}")
    
    # Print summary
    statuses = {}
    for entry in ground_truth:
        status = entry.get("compliance_status")
        if status and status != "TO_REVIEW":
            statuses[status] = statuses.get(status, 0) + 1
    
    print(f"\nSummary:")
    for status, count in statuses.items():
        print(f"  {status}: {count}")

def main():
    """Generate ground truth for all companies"""
    
    print("AI-Powered BRSR Ground Truth Generator")
    print("="*60)
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not found in environment")
        print("Please set it in your .env file or environment")
        return
    
    # Check for PyMuPDF
    try:
        import fitz
    except ImportError:
        print("ERROR: PyMuPDF not installed")
        print("Install with: pip install pymupdf")
        return
    
    companies = ["TCS", "RIL", "TATA Motors"]
    
    for company in companies:
        try:
            generate_ground_truth_for_company(company)
        except Exception as e:
            print(f"\nERROR processing {company}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"Ground Truth Generation Complete!")
    print(f"{'='*60}")
    print(f"\nFiles created in: Company Reports/BRSR Ground Truth/")
    print(f"\nNext: Restart backend to load new ground truth, then generate reports")

if __name__ == "__main__":
    main()
