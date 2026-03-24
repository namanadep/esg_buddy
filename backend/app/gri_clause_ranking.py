"""
GRI clause importance ranking for ground-truth sampling.

Supported clause ID shapes:
- GRI_{standard_num}_{disclosure_id} (e.g. GRI_2_2-1, GRI_305_305-1)
- Short disclosure IDs (e.g. 2-24, 305-1, 2-23-d) as produced by some parsers

Universal standards (GRI 1, 2, 3) are ranked first, then topic standards in a fixed order.
Within a standard, disclosures are sorted naturally (2-2 before 2-10).
"""

from __future__ import annotations

import re
from typing import List, Sequence

# Lower index = more important for sustainability reporting / GRI structure
GRI_STANDARD_PRIORITY: List[str] = [
    "1",  # GRI 1 Foundation
    "2",  # GRI 2 General disclosures
    "3",  # GRI 3 Material topics
    "201",
    "205",
    "207",
    "302",
    "303",
    "305",
    "306",
    "401",
    "403",
    "404",
    "405",
    "413",
]


def _standard_rank(std: str) -> int:
    try:
        return GRI_STANDARD_PRIORITY.index(std)
    except ValueError:
        # Unknown standards: after all known, stable order by numeric value
        if std.isdigit():
            return 500 + int(std)
        return 900


def _disclosure_sort_key(disclosure: str) -> tuple:
    """Natural order for e.g. 2-1, 2-2, 2-10, 305-1-a."""
    parts: List = []
    for segment in re.split(r"[-_]", disclosure):
        if not segment:
            continue
        if segment.isdigit():
            parts.append(int(segment))
        else:
            parts.append(segment.lower())
    return tuple(parts)


def _normalize_clause_id(clause_id: str) -> str:
    s = (clause_id or "").strip()
    if s.lower().startswith("disclosure "):
        s = s[11:].strip()
    return s


def _is_gri_style_clause_id(clause_id: str) -> bool:
    s = _normalize_clause_id(clause_id)
    if s.startswith("GRI_"):
        return True
    # e.g. 2-24, 305-1, 2-23-d, 201-1
    if re.match(r"^\d+-\d+.*", s):
        return True
    # e.g. 2.3 (some parsers)
    if re.match(r"^\d+\.\d+", s):
        return True
    return False


def gri_clause_sort_key(clause_id: str) -> tuple:
    """
    Sort key for one GRI clause_id. Non-GRI ids sort last.
    """
    raw = clause_id
    clause_id = _normalize_clause_id(clause_id)

    if clause_id.startswith("GRI_"):
        rest = clause_id[4:]  # after "GRI_"
        first_underscore = rest.find("_")
        if first_underscore < 0:
            return (9998, (0,), raw)
        std = rest[:first_underscore]
        disclosure = rest[first_underscore + 1 :]
        return (_standard_rank(std), _disclosure_sort_key(disclosure), raw)

    # e.g. 2.4 -> standard 2, disclosure 4
    m_dot = re.match(r"^(\d+)\.(\d+)(.*)$", clause_id)
    if m_dot:
        std = m_dot.group(1)
        disc = m_dot.group(2) + (m_dot.group(3) or "")
        return (_standard_rank(std), _disclosure_sort_key(disc), raw)

    # Short form: "305-1", "2-24", "2-23-d"
    m = re.match(r"^(\d+)-(.+)$", clause_id)
    if m:
        std, rest = m.group(1), m.group(2)
        return (_standard_rank(std), _disclosure_sort_key(rest), raw)

    return (9999, (0,), raw)


def sort_gri_clause_ids(clause_ids: Sequence[str]) -> List[str]:
    """Return clause IDs sorted by GRI importance (most important first)."""
    gri = [c for c in clause_ids if _is_gri_style_clause_id(c)]
    other = [c for c in clause_ids if not _is_gri_style_clause_id(c)]
    gri_sorted = sorted(gri, key=gri_clause_sort_key)
    return list(gri_sorted) + sorted(other)


def select_top_k_gri_clauses(clause_ids: Sequence[str], k: int = 30) -> List[str]:
    """
    From a set of GRI clause IDs (e.g. overlap with a report), keep the k most important.
    """
    if k <= 0:
        return []
    ranked = sort_gri_clause_ids(clause_ids)
    return ranked[:k]


DEFAULT_GRI_GROUND_TRUTH_SAMPLE = 30
