"""Quick ground truth regeneration using actual system clause IDs"""
import json, os, re, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

def get_brsr_clause_ids():
    """Extract BRSR clause IDs from compliance reports"""
    f = open('backend/data/compliance_reports.json', 'r', encoding='utf-8')
    data = f.read()
    f.close()
    ids = re.findall(r'"clause_id": "([^"]+)"', data)
    brsr = sorted(set(x for x in ids if x.startswith('BRSR')))
    return brsr

def analyze_pdf(pdf_path, clause_ids, company):
    """Analyze PDF and generate ground truth"""
    import fitz
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    
    results = []
    batch_size = 40
    
    for i in range(0, len(clause_ids), batch_size):
        batch = clause_ids[i:i+batch_size]
        batch_str = "\n".join(batch)
        
        prompt = f"""Analyze this {company} BRSR report for these clauses. For each, return compliance_status and brief comments.

Report text (first 25000 chars):
{text[:25000]}

Clauses:
{batch_str}

Rules:
- Compliant: disclosure present (data, table, narrative, "0", "Nil", "NA" with reason)
- Partial: some data but key element missing
- Inferred: reasonably inferred from other disclosures
- Non-Compliant: no disclosure at all

Return JSON: {{"results": [{{"clause_id": "...", "compliance_status": "Compliant|Partial|Inferred|Non-Compliant", "comments": "..."}}]}}"""

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            r = json.loads(resp.choices[0].message.content)
            entries = r.get("results", r.get("clauses", []))
            if not entries:
                for k in r:
                    if isinstance(r[k], list):
                        entries = r[k]
                        break
            
            results.extend(entries)
            print(f"  Batch {i//batch_size+1}/{(len(clause_ids)+batch_size-1)//batch_size}: {len(entries)} clauses analyzed", flush=True)
        except Exception as e:
            print(f"  ERROR batch {i//batch_size+1}: {e}", flush=True)
            for cid in batch:
                results.append({"clause_id": cid, "compliance_status": "Non-Compliant", "comments": str(e)})
    
    return results

def main():
    print("=== Ground Truth Regeneration ===", flush=True)
    
    # Get system clause IDs
    print("Extracting clause IDs from reports...", flush=True)
    clause_ids = get_brsr_clause_ids()
    print(f"Found {len(clause_ids)} unique BRSR clause IDs", flush=True)
    print(f"Sample: {clause_ids[:3]}", flush=True)
    
    companies = {
        "TCS": "Company Reports/TCS BRSR.pdf",
        "RIL": "Company Reports/RIL BRSR.pdf",
        "TATA Motors": "Company Reports/TATA Motors BRSR.pdf"
    }
    
    for company, pdf_path in companies.items():
        if not Path(pdf_path).exists():
            print(f"SKIP: {pdf_path} not found", flush=True)
            continue
        
        print(f"\n--- {company} ---", flush=True)
        results = analyze_pdf(pdf_path, clause_ids, company)
        
        # Ensure all clause IDs are covered
        found_ids = {r["clause_id"] for r in results}
        gt = []
        for cid in clause_ids:
            match = next((r for r in results if r.get("clause_id") == cid), None)
            if match:
                gt.append({
                    "clause_id": cid,
                    "compliance_status": match.get("compliance_status", "Non-Compliant"),
                    "comments": match.get("comments", "")
                })
            else:
                gt.append({
                    "clause_id": cid,
                    "compliance_status": "Non-Compliant",
                    "comments": "Not analyzed by AI"
                })
        
        out = Path(f"Company Reports/BRSR Ground Truth/{company} Ground Truth.json")
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(gt, f, indent=2, ensure_ascii=False)
        
        stats = {}
        for e in gt:
            s = e["compliance_status"]
            stats[s] = stats.get(s, 0) + 1
        print(f"Saved {out}: {stats}", flush=True)
    
    print("\n=== DONE ===", flush=True)

if __name__ == "__main__":
    main()
