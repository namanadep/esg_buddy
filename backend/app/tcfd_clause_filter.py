"""
TCFD clause post-processing.

- ``dedupe_tcfd_clauses_by_id``: merge duplicate ``clause_id``s (keep longest description).
  Use after parsing so chunk-level / multi-PDF overlaps do not inflate the index.

- ``filter_tcfd_to_core_recommendations``: optional cap to the 15 official recommended
  disclosures (not used by default).
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from app.models import ESGClause, ESGFramework

# Official recommended disclosure letters per pillar (lowercase)
TCFD_CORE_LETTERS: Dict[str, frozenset] = {
    "Governance": frozenset("abcd"),
    "Strategy": frozenset("abcd"),
    "Risk_Management": frozenset("abcd"),
    "Metrics_and_Targets": frozenset("abc"),
}

PILLAR_ORDER = (
    "Governance",
    "Strategy",
    "Risk_Management",
    "Metrics_and_Targets",
)

_CLAUSE_ID_RE = re.compile(
    r"^TCFD_(Governance|Strategy|Risk_Management|Metrics_and_Targets)_([a-z])\b",
    re.I,
)
_TITLE_LETTER_RE = re.compile(
    r"Recommended\s+disclosure\s*\(?\s*([a-z])\s*\)?|"
    r"\(([a-z])\)\s*[-—]|"
    r"disclosure\s*\(([a-z])\)",
    re.I,
)


def _pillar_from_section(section: Optional[str]) -> Optional[str]:
    if not section:
        return None
    s = re.sub(r"\s+", " ", section.strip().lower()).replace("&", "and")
    if "governance" in s and "strategy" not in s[:20]:
        return "Governance"
    if re.search(r"\bstrategy\b", s):
        return "Strategy"
    if "risk" in s and "management" in s:
        return "Risk_Management"
    if "metric" in s and "target" in s:
        return "Metrics_and_Targets"
    return None


def _letter_from_clause(clause: ESGClause) -> Optional[str]:
    cid = (clause.clause_id or "").strip()
    m = _CLAUSE_ID_RE.match(cid)
    if m:
        return m.group(2).lower()
    m = re.search(r"_([a-z])\s*$", cid, re.I)
    if m and cid.upper().startswith("TCFD_"):
        return m.group(1).lower()
    for blob in (clause.title or "", clause.description or ""):
        tm = _TITLE_LETTER_RE.search(blob)
        if tm:
            for g in tm.groups():
                if g:
                    return g.lower()
    return None


def _pillar_for_clause(clause: ESGClause) -> Optional[str]:
    cid = (clause.clause_id or "").strip()
    m = _CLAUSE_ID_RE.match(cid)
    if m:
        return m.group(1)
    p = _pillar_from_section(clause.section)
    if p:
        return p
    inner = re.sub(r"^TCFD_", "", cid, flags=re.I)
    part = inner.split("_")[0] if inner else ""
    if part.lower() == "governance":
        return "Governance"
    if part.lower() == "strategy":
        return "Strategy"
    if "risk" in part.lower():
        return "Risk_Management"
    if "metric" in part.lower():
        return "Metrics_and_Targets"
    return None


def _canonical_clause_id(pillar: str, letter: str) -> str:
    return f"TCFD_{pillar}_{letter.lower()}"


def _pick_richer(a: ESGClause, b: ESGClause) -> ESGClause:
    la, lb = len(a.description or ""), len(b.description or "")
    if lb > la:
        return b
    if lb < la:
        return a
    return a if len(a.title or "") >= len(b.title or "") else b


def dedupe_tcfd_clauses_by_id(clauses: List[ESGClause]) -> List[ESGClause]:
    """One row per ``clause_id`` (longest description wins). Preserves non-TCFD rows unchanged."""
    tcfd: List[ESGClause] = []
    others: List[ESGClause] = []
    for c in clauses:
        if c.framework == ESGFramework.TCFD:
            tcfd.append(c)
        else:
            others.append(c)
    best: Dict[str, ESGClause] = {}
    for c in tcfd:
        cid = (c.clause_id or "").strip()
        if not cid:
            continue
        if cid not in best:
            best[cid] = c
        else:
            best[cid] = _pick_richer(best[cid], c)
    merged = sorted(best.values(), key=lambda x: (x.clause_id or "").lower())
    return others + merged


def filter_tcfd_to_core_recommendations(clauses: List[ESGClause]) -> List[ESGClause]:
    """
    Keep at most one clause per official (pillar, letter) recommended disclosure.
    Drops non-TCFD clauses in the list and any TCFD row that does not map to a core slot.
    """
    best: Dict[Tuple[str, str], ESGClause] = {}

    for c in clauses:
        if c.framework != ESGFramework.TCFD:
            continue
        pillar = _pillar_for_clause(c)
        letter = _letter_from_clause(c)
        if not pillar or not letter:
            continue
        allowed = TCFD_CORE_LETTERS.get(pillar)
        if not allowed or letter not in allowed:
            continue
        key = (pillar, letter)
        canonical_id = _canonical_clause_id(pillar, letter)
        cur = ESGClause(
            clause_id=canonical_id,
            framework=c.framework,
            section=pillar.replace("_", " "),
            title=c.title or f"Recommended disclosure ({letter}) — {pillar.replace('_', ' ')}",
            description=c.description or "",
            required_evidence_type=c.required_evidence_type,
            mandatory=c.mandatory,
            validation_rules=c.validation_rules,
            keywords=c.keywords,
        )
        if key not in best:
            best[key] = cur
        else:
            richer = _pick_richer(best[key], cur)
            richer.clause_id = canonical_id
            richer.section = pillar.replace("_", " ")
            best[key] = richer

    out: List[ESGClause] = []
    for pillar in PILLAR_ORDER:
        for letter in sorted(TCFD_CORE_LETTERS[pillar]):
            k = (pillar, letter)
            if k in best:
                out.append(best[k])
    return out
