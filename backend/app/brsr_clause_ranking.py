"""
BRSR clause importance ranking for ground-truth sampling.

Top-30 priority: all 9 mandatory Core KPIs first, then General principle-level
disclosures Q1-Q9, then supplementary Q10-Q21.
"""

from __future__ import annotations

from typing import List, Sequence

# Ordered by importance — Core KPIs are mandatory SEBI disclosures; Q1-Q9 are
# principle-level; Q10-Q21 are supplementary. Q22-Q24 are lowest priority.
BRSR_CLAUSE_PRIORITY: List[str] = [
    # 9 mandatory Core KPIs
    "BRSR_Core_1_Green-house_gas_GHG_footprint",
    "BRSR_Core_2_Water_footprint",
    "BRSR_Core_3_Waste_footprint",
    "BRSR_Core_4_Energy_footprint",
    "BRSR_Core_5_Employment_metrics",
    "BRSR_Core_6_Gender_diversity",
    "BRSR_Core_7_Return_to_investors",
    "BRSR_Core_8_Median_remuneration",
    "BRSR_Core_9_Turnover_rate",
    # 9 principle-level General disclosures
    "BRSR_General_Q1",
    "BRSR_General_Q2",
    "BRSR_General_Q3",
    "BRSR_General_Q4",
    "BRSR_General_Q5",
    "BRSR_General_Q6",
    "BRSR_General_Q7",
    "BRSR_General_Q8",
    "BRSR_General_Q9",
    # supplementary General disclosures
    "BRSR_General_Q10",
    "BRSR_General_Q11",
    "BRSR_General_Q12",
    "BRSR_General_Q13",
    "BRSR_General_Q14",
    "BRSR_General_Q15",
    "BRSR_General_Q16",
    "BRSR_General_Q17",
    "BRSR_General_Q18",
    "BRSR_General_Q19",
    "BRSR_General_Q20",
    "BRSR_General_Q21",
    # lowest priority
    "BRSR_General_Q22",
    "BRSR_General_Q23",
    "BRSR_General_Q24",
]

DEFAULT_BRSR_GROUND_TRUTH_SAMPLE = 30


def _brsr_priority_rank(clause_id: str) -> int:
    try:
        return BRSR_CLAUSE_PRIORITY.index(clause_id)
    except ValueError:
        return 999


def sort_brsr_clause_ids(clause_ids: Sequence[str]) -> List[str]:
    """Return clause IDs sorted by BRSR importance (most important first)."""
    return sorted(clause_ids, key=_brsr_priority_rank)


def select_top_k_brsr_clauses(clause_ids: Sequence[str], k: int = 30) -> List[str]:
    """From a set of BRSR clause IDs, keep the k most important."""
    if k <= 0:
        return []
    return sort_brsr_clause_ids(clause_ids)[:k]
