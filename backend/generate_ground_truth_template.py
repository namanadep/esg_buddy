"""
Generate Ground Truth Template for BRSR Reports

This script creates a JSON template with all BRSR clause IDs from the system,
ready to be filled with compliance status for each company (TCS, RIL, TATA Motors).

Usage:
1. Ensure backend is running (uvicorn app.main:app --reload)
2. Run: python backend/generate_ground_truth_template.py
3. Fill in compliance_status for each clause in the generated files
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.clause_parser_enhanced import EnhancedClauseParser
from app.models import ESGFramework

def generate_template():
    """Generate ground truth template with all BRSR clause IDs"""
    
    print("Parsing BRSR standard to extract clause IDs...")
    parser = EnhancedClauseParser()
    
    # Parse BRSR standard
    all_clauses = parser.parse_brsr_standard()
    brsr_clauses = [c for c in all_clauses if c.framework == ESGFramework.BRSR]
    
    print(f"Found {len(brsr_clauses)} BRSR clauses")
    
    # Group by section for better organization
    sections = {}
    for clause in brsr_clauses:
        section = clause.section or "General"
        if section not in sections:
            sections[section] = []
        sections[section].append(clause)
    
    # Create template structure
    template = []
    
    for section_name in sorted(sections.keys()):
        section_clauses = sections[section_name]
        
        # Add section header comment
        template.append({
            "_comment": f"========== {section_name} ({len(section_clauses)} clauses) =========="
        })
        
        for clause in section_clauses:
            template.append({
                "clause_id": clause.clause_id,
                "title": clause.title,
                "description": clause.description[:200] + "..." if len(clause.description) > 200 else clause.description,
                "section": clause.section,
                "mandatory": clause.mandatory,
                "compliance_status": "TO_REVIEW",  # Placeholder - fill with: Compliant, Non-Compliant, Partial, or Inferred
                "comments": ""  # Add notes about why this status was assigned
            })
    
    # Save templates for each company
    companies = ["TCS", "RIL", "TATA Motors"]
    output_dir = Path("Company Reports/BRSR Ground Truth/New")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for company in companies:
        output_file = output_dir / f"{company} Ground Truth - NEW.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        print(f"Created template: {output_file}")
    
    # Also create a summary file
    summary_file = output_dir / "BRSR_Clause_Summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"BRSR Clause Structure Summary\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"Total BRSR Clauses: {len(brsr_clauses)}\n\n")
        
        for section_name in sorted(sections.keys()):
            section_clauses = sections[section_name]
            f.write(f"\n{section_name}: {len(section_clauses)} clauses\n")
            f.write(f"{'-'*60}\n")
            
            for clause in section_clauses:
                f.write(f"  {clause.clause_id}\n")
                f.write(f"    Title: {clause.title}\n")
                f.write(f"    Mandatory: {clause.mandatory}\n\n")
    
    print(f"\nCreated summary: {summary_file}")
    print(f"\nNext steps:")
    print(f"1. Review the TCS BRSR.pdf, RIL BRSR.pdf, and TATA Motors BRSR.pdf documents")
    print(f"2. For each company, fill in 'compliance_status' in the JSON file:")
    print(f"   - 'Compliant' if the clause is fully addressed")
    print(f"   - 'Non-Compliant' if not addressed or missing")
    print(f"   - 'Partial' if partially addressed")
    print(f"   - 'Inferred' if can be inferred from other disclosures")
    print(f"3. Add comments explaining your assessment")
    print(f"4. Remove entries with '_comment' key (those are section headers)")
    print(f"5. Replace the old ground truth files with these new ones")

if __name__ == "__main__":
    try:
        generate_template()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
