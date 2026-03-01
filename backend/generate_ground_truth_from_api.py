"""
Generate Ground Truth Template from Running Backend API

Prerequisites:
1. Backend must be running (uvicorn app.main:app --reload)
2. BRSR clauses must be loaded in ChromaDB

Usage:
    python backend/generate_ground_truth_from_api.py
"""

import requests
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

def fetch_brsr_clauses():
    """Fetch all BRSR clauses from the API"""
    try:
        # Try to get clauses from the search endpoint
        response = requests.post(
            f"{API_BASE}/clauses/search",
            json={
                "framework": "BRSR",
                "query": "disclosure",  # Generic query to get clauses
                "top_k": 500  # Get many clauses
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("clauses", [])
    except Exception as e:
        print(f"Error fetching clauses: {e}")
        return []

def generate_templates():
    """Generate ground truth templates for each company"""
    
    print("Fetching BRSR clauses from API...")
    clauses = fetch_brsr_clauses()
    
    if not clauses:
        print("ERROR: Could not fetch clauses from API.")
        print("Make sure:")
        print("1. Backend is running: uvicorn app.main:app --reload")
        print("2. BRSR clauses are loaded in ChromaDB")
        return
    
    print(f"Found {len(clauses)} clauses")
    
    # Group by section
    sections = {}
    for clause in clauses:
        section = clause.get("section", "General")
        if section not in sections:
            sections[section] = []
        sections[section].append(clause)
    
    # Create template
    template = []
    
    for section_name in sorted(sections.keys()):
        section_clauses = sections[section_name]
        
        # Section header
        template.append({
            "_comment": f"========== {section_name} ({len(section_clauses)} clauses) =========="
        })
        
        for clause in section_clauses:
            template.append({
                "clause_id": clause.get("clause_id"),
                "title": clause.get("title"),
                "description": (clause.get("description", "")[:200] + "...") if len(clause.get("description", "")) > 200 else clause.get("description", ""),
                "section": clause.get("section"),
                "mandatory": clause.get("mandatory", True),
                "compliance_status": "TO_REVIEW",
                "comments": ""
            })
    
    # Save for each company
    companies = ["TCS", "RIL", "TATA Motors"]
    output_dir = Path("Company Reports/BRSR Ground Truth/New")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for company in companies:
        output_file = output_dir / f"{company} Ground Truth - NEW.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Created: {output_file}")
    
    print(f"\n{'='*60}")
    print(f"Next Steps:")
    print(f"{'='*60}")
    print(f"1. Open each company's BRSR PDF (TCS, RIL, TATA Motors)")
    print(f"2. For each clause in the JSON, review the PDF and set:")
    print(f"   - compliance_status: 'Compliant' | 'Non-Compliant' | 'Partial' | 'Inferred'")
    print(f"   - comments: Brief explanation of your assessment")
    print(f"3. Remove entries with '_comment' key (section headers)")
    print(f"4. Move the new files to replace old ground truth files")

if __name__ == "__main__":
    generate_templates()
