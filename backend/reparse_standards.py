"""Call the reparse API to rebuild the vector store.

  python reparse_standards.py          # Reparse ALL frameworks (BRSR, GRI, TCFD, SASB)
  python reparse_standards.py GRI      # Reparse ONLY GRI (e.g. after changing GRI_SCOPE)
"""
import requests
import sys

API = "http://localhost:8000"

def main():
    framework = (sys.argv[1] or "").strip().upper() if len(sys.argv) > 1 else None
    try:
        if framework:
            r = requests.post(f"{API}/system/reparse-framework", params={"framework": framework}, timeout=300)
            r.raise_for_status()
            data = r.json()
            print("Reparse OK:", data.get("message", ""))
            print(f"Framework: {data.get('framework')}, clauses: {data.get('clauses_count')}")
        else:
            r = requests.post(f"{API}/system/reparse-standards", json={}, timeout=300)
            r.raise_for_status()
            data = r.json()
            print("Reparse OK:", data.get("message", ""))
            print("Total clauses:", data.get("total_clauses"))
            print("By framework:", data.get("by_framework"))
    except requests.exceptions.ConnectionError:
        print("Backend not reachable at", API)
        print("Start the backend (e.g. uvicorn app.main:app --reload), then run this again.")
        sys.exit(1)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
