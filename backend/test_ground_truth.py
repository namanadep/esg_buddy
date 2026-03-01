"""
Test Ground Truth Loading

Quick test to verify the new ground truth files load correctly
"""

import json
from pathlib import Path

def test_ground_truth():
    """Test that ground truth files are valid and have correct structure"""
    
    companies = ["TCS", "RIL", "TATA Motors"]
    gt_dir = Path("Company Reports/BRSR Ground Truth")
    
    print("Testing Ground Truth Files")
    print("="*60)
    
    for company in companies:
        file_path = gt_dir / f"{company} Ground Truth.json"
        
        if not file_path.exists():
            print(f"❌ {company}: File not found - {file_path}")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate structure
            valid_entries = 0
            clause_ids = []
            statuses = {"Compliant": 0, "Non-Compliant": 0, "Partial": 0, "Inferred": 0}
            
            for entry in data:
                if "clause_id" in entry and "compliance_status" in entry:
                    valid_entries += 1
                    clause_ids.append(entry["clause_id"])
                    status = entry["compliance_status"]
                    if status in statuses:
                        statuses[status] += 1
            
            print(f"\n✓ {company}:")
            print(f"  File: {file_path}")
            print(f"  Valid entries: {valid_entries}")
            print(f"  Clause IDs: {clause_ids[:3]}...")
            print(f"  Status breakdown:")
            for status, count in statuses.items():
                if count > 0:
                    print(f"    {status}: {count}")
            
        except Exception as e:
            print(f"❌ {company}: Error loading - {e}")
    
    print(f"\n{'='*60}")
    print("Test Complete!")
    print("\nNext Steps:")
    print("1. Restart backend to load new ground truth")
    print("2. Generate a TCS BRSR report")
    print("3. Check accuracy metrics - should show 9 clauses verified")

if __name__ == "__main__":
    test_ground_truth()
