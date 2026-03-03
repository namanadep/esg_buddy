"""Test that ground truth loading works end-to-end"""
import json, sys, os
sys.path.insert(0, 'backend')
os.chdir('backend')

# Simulate what the backend does
from pathlib import Path

# Test path resolution
gt_file = Path(__file__).resolve().parent
print(f"Script location: {gt_file}")

project_root = Path('backend/app/ground_truth_loader.py').resolve().parent.parent.parent
gt_dir = project_root / "Company Reports" / "BRSR Ground Truth"
print(f"Project root: {project_root}")
print(f"GT dir: {gt_dir}")
print(f"GT dir exists: {gt_dir.exists()}")

if gt_dir.exists():
    files = list(gt_dir.glob("*.json"))
    print(f"JSON files: {[f.name for f in files]}")
    
    # Load one and check
    for f in files:
        with open(f, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        print(f"\n{f.name}: {len(data)} entries")
        if data:
            print(f"  First ID: {data[0].get('clause_id')}")
            print(f"  First status: {data[0].get('compliance_status')}")
else:
    print("GT directory NOT FOUND!")
    # Try other paths
    for p in [
        Path("Company Reports/BRSR Ground Truth"),
        Path("../Company Reports/BRSR Ground Truth"),
        Path(__file__).resolve().parent.parent / "Company Reports" / "BRSR Ground Truth",
    ]:
        print(f"  Try: {p} -> exists: {p.exists()}")
