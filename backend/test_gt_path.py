"""Test exact path resolution from ground_truth_loader.py's perspective"""
from pathlib import Path

# Simulate what ground_truth_loader.py does
loader_file = Path("backend/app/ground_truth_loader.py").resolve()
print(f"Loader file: {loader_file}")
print(f"  .parent: {loader_file.parent}")
print(f"  .parent.parent: {loader_file.parent.parent}")
print(f"  .parent.parent.parent: {loader_file.parent.parent.parent}")

project_root = loader_file.parent.parent.parent
gt_dir = project_root / "Company Reports" / "BRSR Ground Truth"
print(f"\nGT dir: {gt_dir}")
print(f"GT dir exists: {gt_dir.exists()}")

if gt_dir.exists():
    import os
    files = os.listdir(str(gt_dir))
    json_files = [f for f in files if f.endswith('.json')]
    print(f"JSON files found: {json_files}")
