"""
Run BRSR, TCFD, GRI, SASB for every uploaded document, skipping pairs that already
have a compliance report. Calls are strictly sequential (one after another).

Requires the API at BASE (default http://127.0.0.1:8000).
"""
from __future__ import annotations

import json
from typing import Set, Tuple
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
FRAMEWORKS = ["BRSR", "TCFD", "GRI", "SASB"]


def _get(path: str) -> dict:
    req = urllib.request.Request(f"{BASE}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def _post_evaluate(document_id: str, framework: str, document_filename: str) -> dict:
    body = json.dumps(
        {
            "document_id": document_id,
            "framework": framework,
            "clause_ids": None,
            "document_filename": document_filename,
        }
    ).encode()
    req = urllib.request.Request(
        f"{BASE}/compliance/evaluate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=None) as r:
        return json.loads(r.read().decode())


def main() -> None:
    docs = _get("/documents").get("documents") or []
    reports = _get("/compliance/reports").get("reports") or []

    existing: Set[Tuple[str, str]] = set()
    for rep in reports:
        did = rep.get("document_id")
        fw = rep.get("framework")
        if did and fw:
            existing.add((did, fw))

    # Stable order: sort by filename, then document_id
    docs.sort(key=lambda d: (d.get("filename") or "", d.get("document_id") or ""))

    jobs: list[tuple[str, str, str]] = []
    for d in docs:
        doc_id = d.get("document_id")
        fn = d.get("filename") or ""
        if not doc_id:
            continue
        for fw in FRAMEWORKS:
            if (doc_id, fw) not in existing:
                jobs.append((doc_id, fw, fn))

    if not jobs:
        print("Nothing to run: every document already has all four framework reports.", flush=True)
        return

    print(
        f"Planned {len(jobs)} scan(s) "
        f"({len(docs)} document(s), {len(existing)} existing report(s)).",
        flush=True,
    )
    for doc_id, fw, fn in jobs:
        print(f"POST {fn!r} / {fw} ...", flush=True)
        try:
            out = _post_evaluate(doc_id, fw, fn)
            print(f"  OK report_id={out.get('report_id')}", flush=True)
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            print(f"  HTTP {e.code}: {err}", flush=True)
            sys.exit(1)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            sys.exit(1)

    print(f"Finished {len(jobs)} scan(s).", flush=True)


if __name__ == "__main__":
    main()
