"""
TCFD clause importance for ground-truth sampling (mirrors GRI top-k idea).

Prefers canonical pillar + letter IDs (Governance → Strategy → Risk_Management → Metrics_and_Targets),
then letter order, then numeric sub-suffix (_1, _2). Other TCFD-shaped and non-TCFD ids follow.
"""

from __future__ import annotations

import re
from typing import List, Sequence

from app.tcfd_clause_filter import PILLAR_ORDER, TCFD_CORE_LETTERS

PILLAR_INDEX = {p: i for i, p in enumerate(PILLAR_ORDER)}

# Official recommended slots first (same letters as TCFD_CORE_LETTERS); then other letters in pillar.
_TCFD_CANON = re.compile(
    r"^TCFD_(Governance|Strategy|Risk_Management|Metrics_and_Targets)_([a-z])(?:_(\d+))?(?:_|$)",
    re.I,
)


def tcfd_clause_sort_key(clause_id: str) -> tuple:
    """Lower tuple = higher priority for ground-truth sampling."""
    raw = (clause_id or "").strip()
    m = _TCFD_CANON.match(raw)
    if m:
        pillar = m.group(1)
        letter = m.group(2).lower()
        sub = int(m.group(3)) if m.group(3) else 0
        pr = PILLAR_INDEX.get(pillar, 99)
        allowed = TCFD_CORE_LETTERS.get(pillar, frozenset())
        if letter in allowed:
            lr = ord(letter) - ord("a")
        else:
            lr = 50 + ord(letter) - ord("a")
        return (pr, lr, sub, raw.lower())
    ru = raw.upper().replace(" ", "")
    # Other TCFD-shaped ids, then disclosure-style, then cross-framework noise (CDP/GRI in TCFD reports).
    if raw.upper().startswith("TCFD_"):
        return (5, 0, 0, raw.lower())
    if ru.startswith("DISCLOSURE") or re.match(r"^(GOV|STR|RM|MT)[-_]", ru):
        return (6, 0, 0, raw.lower())
    return (9, 0, 0, raw.lower())


def sort_tcfd_clause_ids(clause_ids: Sequence[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for cid in sorted(set(clause_ids), key=tcfd_clause_sort_key):
        if cid and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def select_top_k_tcfd_clauses(clause_ids: Sequence[str], k: int = 30) -> List[str]:
    """Keep the k highest-priority TCFD clause IDs present in the report."""
    if k <= 0:
        return []
    ranked = sort_tcfd_clause_ids(clause_ids)
    return ranked[:k]


DEFAULT_TCFD_GROUND_TRUTH_SAMPLE = 30
