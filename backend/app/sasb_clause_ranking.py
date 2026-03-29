"""
SASB clause ordering for ground-truth sampling (stable top-k over report clause IDs).

Prefers ids with the ``SASB_`` prefix first, then lexicographic for reproducibility.
"""

from __future__ import annotations

from typing import List, Sequence

DEFAULT_SASB_GROUND_TRUTH_SAMPLE = 30


def sasb_clause_sort_key(clause_id: str) -> tuple:
    s = (clause_id or "").strip()
    u = s.upper()
    if u.startswith("SASB_"):
        return (0, s.casefold())
    return (1, s.casefold())


def sort_sasb_clause_ids(clause_ids: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for cid in sorted(set(clause_ids), key=sasb_clause_sort_key):
        if cid and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def select_top_k_sasb_clauses(clause_ids: Sequence[str], k: int = 30) -> List[str]:
    if k <= 0:
        return []
    ranked = sort_sasb_clause_ids(clause_ids)
    return ranked[:k]
