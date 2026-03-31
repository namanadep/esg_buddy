"""
Ground Truth Loader for BRSR, GRI, and TCFD Compliance
Loads ground truth labels from JSON files and maps them to the accuracy evaluation system.

BRSR: Company Reports/BRSR Ground Truth/{Company} Ground Truth.json
GRI:   Company Reports/GRI Ground Truth/{Company} GRI Ground Truth.json
TCFD:  Company Reports/TCFD Ground Truth/{Company} TCFD Ground Truth.json
SASB:  Company Reports/SASB Ground Truth/{Company} SASB Ground Truth.json

For GRI reports, only the top N most important clauses (by universal/topic priority) are used
for accuracy — see gri_clause_ranking (default N=30).

For TCFD reports with mapped companies, labels are aligned to the top N ranked clause IDs
from the report — see tcfd_clause_ranking (default N=30).
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional

from app.models import GroundTruthLabel, ComplianceStatus, ESGFramework
from app.gri_clause_ranking import select_top_k_gri_clauses, DEFAULT_GRI_GROUND_TRUTH_SAMPLE
from app.tcfd_clause_ranking import select_top_k_tcfd_clauses, DEFAULT_TCFD_GROUND_TRUTH_SAMPLE
from app.sasb_clause_ranking import select_top_k_sasb_clauses, DEFAULT_SASB_GROUND_TRUTH_SAMPLE
from app.brsr_clause_ranking import select_top_k_brsr_clauses, DEFAULT_BRSR_GROUND_TRUTH_SAMPLE

logger = logging.getLogger(__name__)


class GroundTruthLoader:
    """Load and manage ground truth labels from JSON files"""

    def __init__(
        self,
        ground_truth_dir: str = None,
        gri_ground_truth_dir: str = None,
        tcfd_ground_truth_dir: str = None,
        sasb_ground_truth_dir: str = None,
    ):
        project_root = Path(__file__).resolve().parent.parent.parent
        if ground_truth_dir:
            self.ground_truth_dir = Path(ground_truth_dir)
        else:
            self.ground_truth_dir = project_root / "Company Reports" / "BRSR Ground Truth"
        if gri_ground_truth_dir:
            self.gri_ground_truth_dir = Path(gri_ground_truth_dir)
        else:
            self.gri_ground_truth_dir = project_root / "Company Reports" / "GRI Ground Truth"
        if tcfd_ground_truth_dir:
            self.tcfd_ground_truth_dir = Path(tcfd_ground_truth_dir)
        else:
            self.tcfd_ground_truth_dir = project_root / "Company Reports" / "TCFD Ground Truth"
        if sasb_ground_truth_dir:
            self.sasb_ground_truth_dir = Path(sasb_ground_truth_dir)
        else:
            self.sasb_ground_truth_dir = project_root / "Company Reports" / "SASB Ground Truth"

        self.company_mappings = {
            "TCS": "TCS Ground Truth.json",
            "RIL": "RIL Ground Truth.json",
            "TATA Motors": "TATA Motors Ground Truth.json",
            "Tata Motors": "TATA Motors Ground Truth.json",
            "Sasken": "Sasken Ground Truth.json",
            "Himadri": "Himadri Ground Truth.json",
            "NYK": "NYK Ground Truth.json",
            "Nestle": "Nestle Ground Truth.json",
            "Givaudan": "Givaudan Ground Truth.json",
            "GPM": "GPM Ground Truth.json",
            "Unilever": "Unilever Ground Truth.json",
            "Amazon": "Amazon Ground Truth.json",
            "Apple": "Apple Ground Truth.json",
            "Infosys": "Infosys Ground Truth.json",
        }
        self.gri_company_mappings = {
            "TCS": "TCS GRI Ground Truth.json",
            "RIL": "RIL GRI Ground Truth.json",
            "TATA Motors": "TATA Motors GRI Ground Truth.json",
            "Tata Motors": "TATA Motors GRI Ground Truth.json",
            "Givaudan": "Givaudan GRI Ground Truth.json",
            "GPM": "GPM GRI Ground Truth.json",
            "Unilever": "Unilever GRI Ground Truth.json",
            "Sasken": "Sasken GRI Ground Truth.json",
            "Himadri": "Himadri GRI Ground Truth.json",
            "NYK": "NYK GRI Ground Truth.json",
            "Nestle": "Nestle GRI Ground Truth.json",
            "Amazon": "Amazon GRI Ground Truth.json",
            "Apple": "Apple GRI Ground Truth.json",
            "Infosys": "Infosys GRI Ground Truth.json",
        }
        self.tcfd_company_mappings = {
            "NYK": "NYK TCFD Ground Truth.json",
            "Himadri": "Himadri TCFD Ground Truth.json",
            "Nestle": "Nestle TCFD Ground Truth.json",
            "RIL": "RIL TCFD Ground Truth.json",
            "TCS": "TCS TCFD Ground Truth.json",
            "TATA Motors": "TATA Motors TCFD Ground Truth.json",
            "Tata Motors": "TATA Motors TCFD Ground Truth.json",
            "Sasken": "Sasken TCFD Ground Truth.json",
            "Givaudan": "Givaudan TCFD Ground Truth.json",
            "GPM": "GPM TCFD Ground Truth.json",
            "Unilever": "Unilever TCFD Ground Truth.json",
            "Amazon": "Amazon TCFD Ground Truth.json",
            "Apple": "Apple TCFD Ground Truth.json",
            "Infosys": "Infosys TCFD Ground Truth.json",
        }
        self.sasb_company_mappings = {
            "Amazon": "Amazon SASB Ground Truth.json",
            "Apple": "Apple SASB Ground Truth.json",
            "Infosys": "Infosys SASB Ground Truth.json",
            "RIL": "RIL SASB Ground Truth.json",
            "TCS": "TCS SASB Ground Truth.json",
            "TATA Motors": "TATA Motors SASB Ground Truth.json",
            "Tata Motors": "TATA Motors SASB Ground Truth.json",
            "Sasken": "Sasken SASB Ground Truth.json",
            "Himadri": "Himadri SASB Ground Truth.json",
            "NYK": "NYK SASB Ground Truth.json",
            "Nestle": "Nestle SASB Ground Truth.json",
            "Givaudan": "Givaudan SASB Ground Truth.json",
            "GPM": "GPM SASB Ground Truth.json",
            "Unilever": "Unilever SASB Ground Truth.json",
        }
        logger.info(
            f"Ground truth dirs: BRSR={self.ground_truth_dir} (exists: {self.ground_truth_dir.exists()}), "
            f"GRI={self.gri_ground_truth_dir} (exists: {self.gri_ground_truth_dir.exists()}), "
            f"TCFD={self.tcfd_ground_truth_dir} (exists: {self.tcfd_ground_truth_dir.exists()}), "
            f"SASB={self.sasb_ground_truth_dir} (exists: {self.sasb_ground_truth_dir.exists()})"
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
        use_gri = self._should_use_gri_ground_truth(document_filename, framework)
        use_tcfd = framework == ESGFramework.TCFD
        use_sasb = framework == ESGFramework.SASB

        company_name = self._extract_company_name(document_filename)
        if not company_name:
            logger.warning(f"Could not extract company name from: {document_filename}")
            return []

        if use_tcfd:
            mapping = self.tcfd_company_mappings
            base_dir = self.tcfd_ground_truth_dir
            ground_truth_file = mapping.get(company_name)
            if not ground_truth_file:
                logger.warning(f"No TCFD ground truth mapping for company: {company_name}")
                return []
        elif use_sasb:
            mapping = self.sasb_company_mappings
            base_dir = self.sasb_ground_truth_dir
            ground_truth_file = mapping.get(company_name)
            if not ground_truth_file:
                logger.warning(f"No SASB ground truth mapping for company: {company_name}")
                return []
        elif use_gri:
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

            if use_tcfd and labels and system_clause_ids:
                top_ids = set(
                    select_top_k_tcfd_clauses(
                        system_clause_ids, DEFAULT_TCFD_GROUND_TRUTH_SAMPLE
                    )
                )
                labels = [l for l in labels if l.clause_id in top_ids]
                logger.info(
                    f"TCFD ground truth aligned to top {DEFAULT_TCFD_GROUND_TRUTH_SAMPLE} ranked clauses: "
                    f"{len(labels)} labels for {company_name}"
                )

            if use_sasb and labels and system_clause_ids:
                top_ids = set(
                    select_top_k_sasb_clauses(
                        system_clause_ids, DEFAULT_SASB_GROUND_TRUTH_SAMPLE
                    )
                )
                labels = [l for l in labels if l.clause_id in top_ids]
                logger.info(
                    f"SASB ground truth aligned to top {DEFAULT_SASB_GROUND_TRUTH_SAMPLE} ranked clauses: "
                    f"{len(labels)} labels for {company_name}"
                )

            use_brsr = framework == ESGFramework.BRSR
            if use_brsr and labels and system_clause_ids:
                top_ids = set(
                    select_top_k_brsr_clauses(
                        system_clause_ids, DEFAULT_BRSR_GROUND_TRUTH_SAMPLE
                    )
                )
                labels = [l for l in labels if l.clause_id in top_ids]
                logger.info(
                    f"BRSR ground truth aligned to top {DEFAULT_BRSR_GROUND_TRUTH_SAMPLE} ranked clauses: "
                    f"{len(labels)} labels for {company_name}"
                )

            if use_tcfd:
                fw_label = "TCFD"
            elif use_sasb:
                fw_label = "SASB"
            elif use_gri:
                fw_label = "GRI"
            else:
                fw_label = "BRSR"
            logger.info(
                f"Loaded {len(labels)} ground truth labels for {company_name} "
                f"({fw_label}) from {ground_truth_file}"
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
        """Extract company name from filename (must match gri / BRSR / TCFD mapping keys)."""
        filename_upper = filename.upper()

        if "HIMADRI" in filename_upper:
            return "Himadri"
        if "NESTLE" in filename_upper or "NESTLÉ" in (filename or ""):
            return "Nestle"
        if filename_upper.startswith("NYK") or " NYK" in filename_upper:
            return "NYK"

        stem_tokens = set(re.split(r"[\s_.-]+", Path(filename or "").stem.upper()))
        if "AMAZON" in stem_tokens:
            return "Amazon"
        if "APPLE" in stem_tokens:
            return "Apple"
        if "INFOSYS" in stem_tokens:
            return "Infosys"
        if "SASKEN" in stem_tokens:
            return "Sasken"

        if "SASKEN" in filename_upper:
            return "Sasken"
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

        pages_raw = entry.get("expected_evidence_pages") or []
        expected_pages: List[int] = []
        if isinstance(pages_raw, list):
            for p in pages_raw:
                try:
                    expected_pages.append(int(p))
                except (TypeError, ValueError):
                    continue

        return GroundTruthLabel(
            clause_id=clause_id,
            document_id=document_id,
            expected_status=expected_status,
            expected_evidence_pages=expected_pages,
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
