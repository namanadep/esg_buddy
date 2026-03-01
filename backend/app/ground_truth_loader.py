"""
Ground Truth Loader for BRSR Compliance
Loads ground truth labels from JSON files and maps them to the accuracy evaluation system

Ground truth files now use the same clause IDs as the system (e.g., BRSR_Core_1_Green-house_gas_GHG_footprint)
for direct matching without aggregation.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from app.models import GroundTruthLabel, ComplianceStatus

logger = logging.getLogger(__name__)


class GroundTruthLoader:
    """Load and manage ground truth labels from JSON files"""
    
    def __init__(self, ground_truth_dir: str = "Company Reports/BRSR Ground Truth"):
        self.ground_truth_dir = Path(ground_truth_dir)
        self.company_mappings = {
            "TCS": "TCS Ground Truth.json",
            "RIL": "RIL Ground Truth.json",
            "TATA Motors": "TATA Motors Ground Truth.json",
            "Tata Motors": "TATA Motors Ground Truth.json"
        }
    
    def load_ground_truth_for_document(
        self, 
        document_id: str, 
        document_filename: str,
        system_clause_ids: Optional[List[str]] = None
    ) -> List[GroundTruthLabel]:
        """
        Load ground truth labels for a specific document
        
        Args:
            document_id: The document ID from the system
            document_filename: The filename (e.g., "TCS BRSR.pdf")
            system_clause_ids: Optional list of clause IDs from the system's evaluation (for filtering)
        
        Returns:
            List of GroundTruthLabel objects
        """
        # Extract company name from filename
        company_name = self._extract_company_name(document_filename)
        
        if not company_name:
            logger.warning(f"Could not extract company name from: {document_filename}")
            return []
        
        # Find corresponding ground truth file
        ground_truth_file = self.company_mappings.get(company_name)
        
        if not ground_truth_file:
            logger.warning(f"No ground truth mapping for company: {company_name}")
            return []
        
        file_path = self.ground_truth_dir / ground_truth_file
        
        if not file_path.exists():
            logger.warning(f"Ground truth file not found: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Convert to GroundTruthLabel objects
            labels = []
            for entry in raw_data:
                try:
                    label = self._convert_to_ground_truth_label(entry, document_id)
                    if label:
                        # Filter by system clause IDs if provided
                        if system_clause_ids is None or label.clause_id in system_clause_ids:
                            labels.append(label)
                except Exception as e:
                    logger.warning(f"Error converting entry {entry.get('clause_id')}: {e}")
                    continue
            
            logger.info(f"Loaded {len(labels)} ground truth labels for {company_name} from {ground_truth_file}")
            return labels
            
        except Exception as e:
            logger.error(f"Error loading ground truth from {file_path}: {e}")
            return []
    
    def _extract_company_name(self, filename: str) -> Optional[str]:
        """Extract company name from filename"""
        filename_upper = filename.upper()
        
        # Check for each company
        if "TCS" in filename_upper:
            return "TCS"
        elif "RIL" in filename_upper or "RELIANCE" in filename_upper:
            return "RIL"
        elif "TATA" in filename_upper:
            return "TATA Motors"
        
        return None
    
    def _convert_to_ground_truth_label(
        self, 
        entry: Dict, 
        document_id: str
    ) -> Optional[GroundTruthLabel]:
        """
        Convert ground truth JSON entry to GroundTruthLabel
        
        Ground truth format:
        {
            "clause_id": "BRSR-Core-...",
            "compliance_status": "Compliant" | "Non-Compliant" | "Partial",
            "comments": "..."
        }
        """
        clause_id = entry.get("clause_id")
        compliance_status = entry.get("compliance_status", "").strip()
        comments = entry.get("comments", "")
        
        if not clause_id:
            return None
        
        # Clause IDs in new ground truth files already match system format
        # No normalization needed
        
        # Map compliance_status to ComplianceStatus enum
        status_map = {
            "compliant": ComplianceStatus.SUPPORTED,
            "non-compliant": ComplianceStatus.NOT_SUPPORTED,
            "partial": ComplianceStatus.PARTIAL,
            "inferred": ComplianceStatus.INFERRED
        }
        
        expected_status = status_map.get(
            compliance_status.lower(),
            ComplianceStatus.NOT_SUPPORTED
        )
        
        # Ground truth files don't include page numbers, so we use empty list
        # (retrieval recall won't be calculated without page numbers)
        return GroundTruthLabel(
            clause_id=clause_id,
            document_id=document_id,
            expected_status=expected_status,
            expected_evidence_pages=[],
            notes=comments
        )
    
    def load_all_ground_truth(self) -> Dict[str, List[GroundTruthLabel]]:
        """
        Load all ground truth files
        
        Returns:
            Dict mapping company name to list of labels
        """
        all_labels = {}
        
        for company, filename in self.company_mappings.items():
            file_path = self.ground_truth_dir / filename
            
            if not file_path.exists():
                logger.warning(f"Ground truth file not found: {file_path}")
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                
                labels = []
                for entry in raw_data:
                    # Use placeholder document_id since we don't know it yet
                    label = self._convert_to_ground_truth_label(entry, f"placeholder_{company}")
                    if label:
                        labels.append(label)
                
                all_labels[company] = labels
                logger.info(f"Loaded {len(labels)} labels for {company}")
                
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
                continue
        
        return all_labels
