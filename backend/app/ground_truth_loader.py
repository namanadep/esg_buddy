"""
Ground Truth Loader for BRSR and GRI Compliance
Loads ground truth labels from JSON files and maps them to the accuracy evaluation system.

BRSR: Company Reports/BRSR Ground Truth/{Company} Ground Truth.json
GRI:   Company Reports/GRI Ground Truth/{Company} GRI Ground Truth.json

For GRI reports, only the top N most important clauses (by universal/topic priority) are used
for accuracy — see gri_clause_ranking.select_top_k_gri_clauses (default N=30).
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from app.models import GroundTruthLabel, ComplianceStatus, ESGFramework
from app.gri_clause_ranking import select_top_k_gri_clauses, DEFAULT_GRI_GROUND_TRUTH_SAMPLE

logger = logging.getLogger(__name__)


class GroundTruthLoader:
    """Load and manage ground truth labels from JSON files"""

    def __init__(self, ground_truth_dir: str = None, gri_ground_truth_dir: str = None):
        project_root = Path(__file__).resolve().parent.parent.parent
        if ground_truth_dir:
            self.ground_truth_dir = Path(ground_truth_dir)
        else:
            self.ground_truth_dir = project_root / "Company Reports" / "BRSR Ground Truth"
        if gri_ground_truth_dir:
            self.gri_ground_truth_dir = Path(gri_ground_truth_dir)
        else:
            self.gri_ground_truth_dir = project_root / "Company Reports" / "GRI Ground Truth"

        self.company_mappings = {
            "TCS": "TCS Ground Truth.json",
            "RIL": "RIL Ground Truth.json",
            "TATA Motors": "TATA Motors Ground Truth.json",
            "Tata Motors": "TATA Motors Ground Truth.json",
        }
        self.gri_company_mappings = {
            "TCS": "TCS GRI Ground Truth.json",
            "RIL": "RIL GRI Ground Truth.json",
            "TATA Motors": "TATA Motors GRI Ground Truth.json",
            "Tata Motors": "TATA Motors GRI Ground Truth.json",
            "Givaudan": "Givaudan GRI Ground Truth.json",
            "GPM": "GPM GRI Ground Truth.json",
            "Unilever": "Unilever GRI Ground Truth.json",
        }
        logger.info(
            f"Ground truth dirs: BRSR={self.ground_truth_dir} (exists: {self.ground_truth_dir.exists()}), "
            f"GRI={self.gri_ground_truth_dir} (exists: {self.gri_ground_truth_dir.exists()})"
        )

    def load_ground_truth_for_document(
        self,
        document_id: str,
        document_filename: str,
        system_clause_ids: Optional[List[str]] = None,
        framework: Optional[ESGFramework] = None,
    ) -> List[GroundTruthLabel]:
        """
        Load ground truth labels for a specific document.

        Args:
            document_id: The document ID from the system
            document_filename: The filename (e.g., "TCS BRSR.pdf", "RIL GRI.pdf")
            system_clause_ids: Optional list of clause IDs from the report (for filtering)
            framework: Report framework; when set, selects BRSR vs GRI ground-truth files

        Returns:
            List of GroundTruthLabel objects (for GRI, at most DEFAULT_GRI_GROUND_TRUTH_SAMPLE
            clauses — the most important among those present in the report).
        """
        if framework in (ESGFramework.SASB, ESGFramework.TCFD):
            return []

        use_gri = self._should_use_gri_ground_truth(document_filename, framework)

        company_name = self._extract_company_name(document_filename)
        if not company_name:
            logger.warning(f"Could not extract company name from: {document_filename}")
            return []

        if use_gri:
            mapping = self.gri_company_mappings
            base_dir = self.gri_ground_truth_dir
            ground_truth_file = mapping.get(company_name)
        else:
            mapping = self.company_mappings
            base_dir = self.ground_truth_dir
            ground_truth_file = mapping.get(company_name)

        if not ground_truth_file:
            logger.warning(f"No ground truth mapping for company: {company_name}")
            return []

        file_path = base_dir / ground_truth_file

        if not file_path.exists():
            logger.warning(f"Ground truth file not found: {file_path}")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            labels: List[GroundTruthLabel] = []
            for entry in raw_data:
                try:
                    label = self._convert_to_ground_truth_label(entry, document_id)
                    if label:
                        if system_clause_ids is None or label.clause_id in system_clause_ids:
                            labels.append(label)
                except Exception as e:
                    logger.warning(f"Error converting entry {entry.get('clause_id')}: {e}")
                    continue

            if use_gri and labels:
                clause_ids = [l.clause_id for l in labels]
                top_ids = set(
                    select_top_k_gri_clauses(clause_ids, DEFAULT_GRI_GROUND_TRUTH_SAMPLE)
                )
                labels = [l for l in labels if l.clause_id in top_ids]
                logger.info(
                    f"GRI ground truth sampled to {len(labels)} clauses (cap={DEFAULT_GRI_GROUND_TRUTH_SAMPLE}) "
                    f"for {company_name}"
                )

            logger.info(
                f"Loaded {len(labels)} ground truth labels for {company_name} "
                f"({'GRI' if use_gri else 'BRSR'}) from {ground_truth_file}"
            )
            return labels

        except Exception as e:
            logger.error(f"Error loading ground truth from {file_path}: {e}")
            return []

    @staticmethod
    def _should_use_gri_ground_truth(
        document_filename: str, framework: Optional[ESGFramework]
    ) -> bool:
        if framework == ESGFramework.GRI:
            return True
        if framework == ESGFramework.BRSR:
            return False
        fn = document_filename.upper()
        if "GRI" in fn and "BRSR" not in fn:
            return True
        return False

    def _extract_company_name(self, filename: str) -> Optional[str]:
        """Extract company name from filename (must match gri_company_mappings / company_mappings keys)."""
        filename_upper = filename.upper()

        if "GIVAUDAN" in filename_upper:
            return "Givaudan"
        if "UNILEVER" in filename_upper:
            return "Unilever"
        if "GPM" in filename_upper:
            return "GPM"
        if "TCS" in filename_upper:
            return "TCS"
        if "RIL" in filename_upper or "RELIANCE" in filename_upper:
            return "RIL"
        if "TATA" in filename_upper:
            return "TATA Motors"

        return None

    def _convert_to_ground_truth_label(
        self, entry: Dict, document_id: str
    ) -> Optional[GroundTruthLabel]:
        """
        Convert ground truth JSON entry to GroundTruthLabel

        Ground truth format:
        {
            "clause_id": "...",
            "compliance_status": "Compliant" | "Non-Compliant" | "Partial",
            "comments": "..."
        }
        """
        clause_id = entry.get("clause_id")
        compliance_status = entry.get("compliance_status", "").strip()
        comments = entry.get("comments", "")

        if not clause_id:
            return None

        status_map = {
            "compliant": ComplianceStatus.SUPPORTED,
            "non-compliant": ComplianceStatus.NOT_SUPPORTED,
            "partial": ComplianceStatus.PARTIAL,
            "inferred": ComplianceStatus.PARTIAL,
        }

        expected_status = status_map.get(
            compliance_status.lower(),
            ComplianceStatus.NOT_SUPPORTED,
        )

        return GroundTruthLabel(
            clause_id=clause_id,
            document_id=document_id,
            expected_status=expected_status,
            expected_evidence_pages=[],
            notes=comments,
        )

    def load_all_ground_truth(self) -> Dict[str, List[GroundTruthLabel]]:
        """
        Load all BRSR ground truth files (legacy helper).

        For mixed BRSR + GRI deployments, prefer loading per report via load_ground_truth_for_document
        with framework set.
        """
        all_labels: Dict[str, List[GroundTruthLabel]] = {}

        for company, filename in self.company_mappings.items():
            file_path = self.ground_truth_dir / filename

            if not file_path.exists():
                logger.warning(f"Ground truth file not found: {file_path}")
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

                labels = []
                for entry in raw_data:
                    label = self._convert_to_ground_truth_label(entry, f"placeholder_{company}")
                    if label:
                        labels.append(label)

                all_labels[company] = labels
                logger.info(f"Loaded {len(labels)} BRSR labels for {company}")

            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
                continue

        return all_labels
