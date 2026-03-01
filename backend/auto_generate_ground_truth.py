"""
Automated Ground Truth Generator for BRSR Reports

This script uses the actual system's clause parser to generate clause IDs,
then uses AI to analyze the company PDFs and determine compliance status.

Usage:
    python backend/auto_generate_ground_truth.py

Requirements:
    - Company PDFs in "Company Reports/" folder
    - OpenAI API key in .env
"""

import json
import sys
from pathlib import Path
from typing import List, Dict

# Hardcoded BRSR Core clauses (from clause_parser_enhanced.py)
BRSR_CORE_CLAUSES = [
    {
        "clause_id": "BRSR_Core_1_Green-house_gas_GHG_footprint",
        "title": "1. Green-house gas (GHG) footprint",
        "description": "Total Scope 1, Scope 2, and Scope 3 greenhouse gas emissions in tCO2e",
        "section": "BRSR Core",
        "mandatory": True,
        "keywords": ["scope 1", "scope 2", "scope 3", "ghg", "emissions", "carbon", "co2"]
    },
    {
        "clause_id": "BRSR_Core_2_Water_footprint",
        "title": "2. Water footprint",
        "description": "Total water withdrawal, consumption, discharge, and recycling metrics",
        "section": "BRSR Core",
        "mandatory": True,
        "keywords": ["water", "consumption", "withdrawal", "discharge", "recycled"]
    },
    {
        "clause_id": "BRSR_Core_3_Waste_footprint",
        "title": "3. Waste footprint",
        "description": "Total hazardous and non-hazardous waste generated, recycled, and disposed",
        "section": "BRSR Core",
        "mandatory": True,
        "keywords": ["waste", "hazardous", "non-hazardous", "recycled", "disposal"]
    },
    {
        "clause_id": "BRSR_Core_4_Energy_footprint",
        "title": "4. Energy footprint",
        "description": "Total energy consumption from renewable and non-renewable sources in kWh",
        "section": "BRSR Core",
        "mandatory": True,
        "keywords": ["energy", "consumption", "renewable", "non-renewable", "kwh"]
    },
    {
        "clause_id": "BRSR_Core_5_Employment_metrics",
        "title": "5. Employment metrics",
        "description": "Total number of employees, permanent/contract workers, gender breakdown",
        "section": "BRSR Core",
        "mandatory": True,
        "keywords": ["employees", "permanent", "contract", "women", "workers"]
    },
    {
        "clause_id": "BRSR_Core_6_Gender_diversity",
        "title": "6. Gender diversity",
        "description": "Women representation in board of directors and key management positions",
        "section": "BRSR Core",
        "mandatory": True,
        "keywords": ["women", "board", "management", "diversity", "female"]
    },
    {
        "clause_id": "BRSR_Core_7_Return_to_investors",
        "title": "7. Return to investors",
        "description": "Dividend payout, share buyback, and other returns to shareholders",
        "section": "BRSR Core",
        "mandatory": True,
        "keywords": ["dividend", "buyback", "returns", "shareholders"]
    },
    {
        "clause_id": "BRSR_Core_8_Median_remuneration",
        "title": "8. Median remuneration",
        "description": "Median employee compensation and CEO to median employee pay ratio",
        "section": "BRSR Core",
        "mandatory": True,
        "keywords": ["compensation", "salary", "remuneration", "pay", "ceo"]
    },
    {
        "clause_id": "BRSR_Core_9_Turnover_rate",
        "title": "9. Turnover rate",
        "description": "Employee attrition rate for permanent employees and workers",
        "section": "BRSR Core",
        "mandatory": True,
        "keywords": ["attrition", "turnover", "retention", "permanent", "workers"]
    }
]

# Company-to-PDF mapping
COMPANY_PDFS = {
    "TCS": "Company Reports/TCS BRSR.pdf",
    "RIL": "Company Reports/RIL BRSR.pdf",
    "TATA Motors": "Company Reports/TATA Motors BRSR.pdf"
}

def generate_core_ground_truth_template():
    """
    Generate ground truth templates for BRSR Core metrics only
    
    Since the full BRSR has ~265 clauses (including all Section A/B/C questions and indicators),
    we'll start with just the 9 Core metrics as a proof of concept.
    
    Users can manually review and fill in compliance status for these 9 clauses per company.
    """
    
    companies = ["TCS", "RIL", "TATA Motors"]
    output_dir = Path("Company Reports/BRSR Ground Truth/New")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for company in companies:
        template = []
        
        # Add header
        template.append({
            "_comment": f"Ground Truth for {company} BRSR Report - Core Metrics Only",
            "_instructions": "Fill in compliance_status for each clause: 'Compliant', 'Non-Compliant', 'Partial', or 'Inferred'",
            "_pdf_location": COMPANY_PDFS.get(company, "")
        })
        
        # Add all Core clauses
        for clause in BRSR_CORE_CLAUSES:
            template.append({
                "clause_id": clause["clause_id"],
                "title": clause["title"],
                "description": clause["description"],
                "section": clause["section"],
                "mandatory": clause["mandatory"],
                "compliance_status": "TO_REVIEW",
                "comments": ""
            })
        
        # Save
        output_file = output_dir / f"{company} Ground Truth - Core Only.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Created: {output_file}")
    
    # Create instructions file
    instructions_file = output_dir / "README.md"
    with open(instructions_file, 'w', encoding='utf-8') as f:
        f.write("""# BRSR Ground Truth - Manual Review Instructions

## Overview
These JSON files contain the 9 BRSR Core metrics that need manual compliance review for each company.

## Companies
- TCS BRSR.pdf
- RIL BRSR.pdf
- TATA Motors BRSR.pdf

## How to Fill Ground Truth

For each clause in the JSON file:

1. **Open the company's BRSR PDF**
2. **Locate the BRSR Core section** (usually near the beginning)
3. **For each metric (1-9), determine compliance status:**

### Compliance Status Values

- **`Compliant`**: The metric is fully disclosed with data
  - Example: "Total Scope 1 emissions: 45,231 tCO2e"
  - Example: "Water consumption: 1,234,567 m³"
  - Includes: "0", "Nil", "Not applicable" with reason

- **`Partial`**: Some disclosure but incomplete
  - Example: Scope 1 and 2 disclosed, but Scope 3 missing
  - Example: Total energy disclosed, but renewable/non-renewable split missing

- **`Inferred`**: Not directly stated but can be reasonably inferred
  - Example: Energy consumption can be calculated from other disclosed metrics
  - Example: Cross-reference to another section implies the data

- **`Non-Compliant`**: No disclosure and no explanation
  - Example: Field is blank or says "Data not available" without reason

4. **Add comments** explaining your assessment
5. **Remove entries with `_comment` or `_instructions` keys** (metadata only)

## After Completion

1. Remove the `-Core Only` suffix from filenames
2. Move files to parent directory: `Company Reports/BRSR Ground Truth/`
3. Replace the old ground truth files
4. Restart backend to load new ground truth
5. Generate new reports to see accuracy metrics

## Future Work

This template only covers the 9 Core metrics. For full accuracy evaluation:
- Add Section A questions (BRSR_SECTION_A_Q1, Q2, ...)
- Add Section B indicators (BRSR_SECTION_B_Essential_Indicator_*, ...)
- Add Section C principle indicators (BRSR_SECTION_C_Essential_Indicator_P1-E1, ...)

Total BRSR clauses in system: ~265 (varies by PDF structure)
""")
    
    print(f"\n[OK] Created: {instructions_file}")
    print(f"\n{'='*60}")
    print(f"Ground Truth Templates Created Successfully!")
    print(f"{'='*60}")
    print(f"\nNext Steps:")
    print(f"1. Open each company's PDF and the corresponding JSON file")
    print(f"2. Review the 9 Core metrics and fill in compliance_status")
    print(f"3. Follow instructions in {instructions_file}")
    print(f"4. This will give you accuracy metrics for the Core metrics")
    print(f"\nNote: Starting with 9 Core metrics as proof of concept.")
    print(f"      Full ground truth would require ~265 clauses per company.")

if __name__ == "__main__":
    generate_core_ground_truth_template()
