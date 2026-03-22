"""
One-time migration: rewrite existing BRSR ground truth JSON files so any
compliance_status of "Inferred" / "inferred" becomes "Partial".

Does not call OpenAI. Run:
  cd backend && python migrate_ground_truth_remove_inferred.py
"""

import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
GT_DIR = PROJECT_ROOT / "Company Reports" / "BRSR Ground Truth"

FILES = [
    "TCS Ground Truth.json",
    "RIL Ground Truth.json",
    "TATA Motors Ground Truth.json",
]


def main():
    if not GT_DIR.exists():
        print(f"No directory: {GT_DIR}")
        return
    for name in FILES:
        path = GT_DIR / name
        if not path.exists():
            print(f"Skip (missing): {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        changed = 0
        for row in data:
            s = row.get("compliance_status", "")
            if str(s).strip().lower() == "inferred":
                row["compliance_status"] = "Partial"
                changed += 1
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"{name}: updated {changed} Inferred -> Partial")
    print("Done.")


if __name__ == "__main__":
    main()
