"""Verify ground truth clause IDs match system clause IDs"""
import json, re

# Load system clause IDs from reports
with open('backend/data/compliance_reports.json', 'r', encoding='utf-8') as f:
    data = f.read()
system_ids = set(x for x in re.findall(r'"clause_id": "([^"]+)"', data) if x.startswith('BRSR'))

# Load ground truth clause IDs
for company in ["TCS", "RIL", "TATA Motors"]:
    gt_file = f"Company Reports/BRSR Ground Truth/{company} Ground Truth.json"
    with open(gt_file, 'r', encoding='utf-8') as f:
        gt = json.load(f)
    
    gt_ids = set(e["clause_id"] for e in gt)
    
    matches = gt_ids & system_ids
    gt_only = gt_ids - system_ids
    sys_only = system_ids - gt_ids
    
    print(f"\n{company}:")
    print(f"  Ground truth clauses: {len(gt_ids)}")
    print(f"  System clauses: {len(system_ids)}")
    print(f"  Matches: {len(matches)}")
    print(f"  GT only (not in system): {len(gt_only)}")
    print(f"  System only (not in GT): {len(sys_only)}")
    
    if gt_only:
        print(f"  Sample GT-only: {list(gt_only)[:3]}")
    if sys_only:
        print(f"  Sample Sys-only: {list(sys_only)[:3]}")
