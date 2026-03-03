import json
import re

with open('backend/data/compliance_reports.json', 'r', encoding='utf-8') as f:
    data = f.read()

ids = re.findall(r'"clause_id": "([^"]+)"', data)
unique = sorted(set(ids))

brsr_core = [x for x in unique if 'Core' in x]

print(f"Total unique clause IDs: {len(unique)}")
print(f"BRSR Core clause IDs ({len(brsr_core)}):")
for cid in brsr_core[:20]:
    print(f"  {cid}")

print(f"\nFirst 10 BRSR clause IDs:")
brsr_all = [x for x in unique if x.startswith('BRSR')]
for cid in brsr_all[:10]:
    print(f"  {cid}")
