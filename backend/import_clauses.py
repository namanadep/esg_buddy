"""
Import pre-parsed clauses from JSON file into the vector store
Use this after parsing clauses on a separate machine with more memory
"""

import sys
import json
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.models import ESGClause, ESGFramework, EvidenceType, ValidationRule
from app.vector_store import VectorStore
from app.config import settings

def load_clauses_from_json(json_path: Path):
    """Load clauses from JSON file and convert to ESGClause objects"""
    print(f"Loading clauses from {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    framework_str = data.get("framework", "UNKNOWN")
    clauses_data = data.get("clauses", [])
    
    print(f"Framework: {framework_str}")
    print(f"Total clauses in file: {len(clauses_data)}")
    print()
    
    clauses = []
    for clause_data in clauses_data:
        try:
            # Convert evidence types
            evidence_types = [
                EvidenceType(et) for et in clause_data.get("required_evidence_type", [])
            ]
            
            # Convert validation rules
            validation_rules = []
            for rule_data in clause_data.get("validation_rules", []):
                validation_rules.append(ValidationRule(
                    rule_id=rule_data["rule_id"],
                    rule_type=rule_data["rule_type"],
                    description=rule_data["description"],
                    parameters=rule_data["parameters"],
                    mandatory=rule_data.get("mandatory", False)
                ))
            
            # Create clause
            clause = ESGClause(
                clause_id=clause_data["clause_id"],
                framework=ESGFramework(clause_data["framework"]),
                section=clause_data.get("section"),
                title=clause_data["title"],
                description=clause_data["description"],
                required_evidence_type=evidence_types,
                mandatory=clause_data.get("mandatory", True),
                validation_rules=validation_rules,
                keywords=clause_data.get("keywords", [])
            )
            clauses.append(clause)
            
        except Exception as e:
            print(f"Warning: Failed to convert clause {clause_data.get('clause_id', '?')}: {e}")
    
    print(f"✓ Converted {len(clauses)} clauses")
    return clauses, framework_str

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_clauses.py <json_file>")
        print("Example: python import_clauses.py tcfd_clauses.json")
        sys.exit(1)
    
    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"Error: File not found: {json_file}")
        sys.exit(1)
    
    print("=" * 80)
    print("ESGBuddy Clause Importer")
    print("=" * 80)
    print()
    
    # Load clauses from JSON
    clauses, framework = load_clauses_from_json(json_file)
    
    if not clauses:
        print("No clauses to import")
        sys.exit(0)
    
    # Initialize vector store
    print("Initializing vector store...")
    vector_store = VectorStore()
    
    # Clear existing clauses for this framework
    print(f"Clearing existing {framework} clauses from vector store...")
    vector_store.clear_clauses(framework)
    
    # Add new clauses
    print(f"Adding {len(clauses)} clauses to vector store...")
    vector_store.add_clauses(clauses)
    
    print()
    print("=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    print(f"Imported {len(clauses)} {framework} clauses into vector store")
    print()
    print("Restart the backend to load these clauses into memory for the API.")
    print()

if __name__ == "__main__":
    main()
