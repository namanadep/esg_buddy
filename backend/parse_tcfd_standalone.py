"""
Standalone TCFD Parser for HPC Node
Run this on a machine with sufficient memory to parse TCFD documents
Exports clauses to JSON for import on the main system
"""

import sys
import json
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.clause_parser_enhanced import EnhancedClauseParser
from app.models import ESGFramework

def main():
    print("=" * 80)
    print("TCFD Standalone Parser for HPC Node")
    print("=" * 80)
    print()
    
    # Configuration
    standards_dir = Path("../Standards")  # Adjust if needed
    output_file = Path("tcfd_clauses.json")
    
    print(f"Standards directory: {standards_dir.resolve()}")
    print(f"Output file: {output_file.resolve()}")
    print()
    
    # Initialize parser with LLM enabled
    print("Initializing parser with LLM enabled...")
    parser = EnhancedClauseParser(use_llm=True)
    parser.standards_dir = standards_dir
    
    # Parse TCFD
    print("Parsing TCFD documents...")
    print(f"TCFD directory: {standards_dir / 'TCFD'}")
    print()
    
    try:
        tcfd_clauses = parser.parse_framework(ESGFramework.TCFD)
        print(f"\n✓ Successfully parsed {len(tcfd_clauses)} TCFD clauses")
        print()
        
        # Convert to JSON-serializable format
        print("Converting clauses to JSON format...")
        clauses_json = []
        for clause in tcfd_clauses:
            clauses_json.append({
                "clause_id": clause.clause_id,
                "framework": clause.framework.value,
                "section": clause.section,
                "title": clause.title,
                "description": clause.description,
                "required_evidence_type": [et.value for et in clause.required_evidence_type],
                "mandatory": clause.mandatory,
                "validation_rules": [
                    {
                        "rule_id": rule.rule_id,
                        "rule_type": rule.rule_type,
                        "description": rule.description,
                        "parameters": rule.parameters,
                        "mandatory": rule.mandatory
                    }
                    for rule in clause.validation_rules
                ],
                "keywords": clause.keywords
            })
        
        # Save to JSON
        print(f"Saving to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "framework": "TCFD",
                "total_clauses": len(clauses_json),
                "clauses": clauses_json
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved {len(clauses_json)} clauses to {output_file}")
        print()
        print("=" * 80)
        print("SUCCESS!")
        print("=" * 80)
        print()
        print("Next steps:")
        print(f"1. Transfer '{output_file}' to your laptop")
        print("2. Place it in the backend/ directory")
        print("3. Run: python import_clauses.py tcfd_clauses.json")
        print("   Or use the API: POST /system/import-clauses")
        print()
        
    except Exception as e:
        print(f"\n✗ Error parsing TCFD: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
