"""
ESGBuddy ESG Clause Parser
Parses ESG standard PDFs into structured clauses
"""

import re
import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path

from app.models import (
    ESGClause, 
    ESGFramework, 
    EvidenceType, 
    ValidationRule
)
from app.config import settings

logger = logging.getLogger(__name__)


class ClauseParser:
    """Parse ESG standard documents into structured clauses"""
    
    def __init__(self):
        self.standards_dir = Path(settings.standards_dir)
    
    def parse_all_standards(self) -> List[ESGClause]:
        """Parse all ESG standards from the Standards directory"""
        clauses = []
        
        # Parse GRI standards
        clauses.extend(self.parse_gri_standards())
        
        # Parse BRSR
        clauses.extend(self.parse_brsr_standard())
        
        # Parse SASB
        clauses.extend(self.parse_sasb_standard())
        
        # Parse TCFD
        clauses.extend(self.parse_tcfd_standard())
        
        logger.info(f"Parsed {len(clauses)} total clauses from all standards")
        return clauses
    
    # ============= GRI Parser =============
    
    def parse_gri_standards(self) -> List[ESGClause]:
        """Parse all GRI standard PDFs"""
        gri_dir = self.standards_dir / "GRI"
        if not gri_dir.exists():
            logger.warning(f"GRI directory not found: {gri_dir}")
            return []
        
        clauses = []
        gri_files = list(gri_dir.glob("*.pdf"))
        
        logger.info(f"Found {len(gri_files)} GRI standard files")
        
        for pdf_path in gri_files:
            try:
                file_clauses = self._parse_gri_document(pdf_path)
                clauses.extend(file_clauses)
                logger.info(f"Parsed {len(file_clauses)} clauses from {pdf_path.name}")
            except Exception as e:
                logger.error(f"Error parsing {pdf_path.name}: {e}")
        
        return clauses
    
    def _parse_gri_document(self, pdf_path: Path) -> List[ESGClause]:
        """Parse a single GRI standard document"""
        doc = fitz.open(str(pdf_path))
        clauses = []
        
        # Extract GRI standard number from filename
        filename = pdf_path.stem
        standard_match = re.search(r'GRI (\d+[a-z]?)_', filename)
        standard_num = standard_match.group(1) if standard_match else "Unknown"
        
        # Extract topic name
        topic = filename.split('_', 1)[1] if '_' in filename else "General"
        topic = re.sub(r'\s+\d{4}', '', topic).strip()  # Remove year
        
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        
        doc.close()
        
        # GRI standards have "Disclosure" sections
        # Pattern: "Disclosure XXX-Y" or "Disclosure XXX-Y-a"
        disclosure_pattern = r'Disclosure\s+(\d+-\d+(?:-[a-z])?)[:\s]+(.*?)(?=Disclosure\s+\d+-\d+|$)'
        matches = re.finditer(disclosure_pattern, full_text, re.DOTALL | re.IGNORECASE)
        
        clause_counter = 0
        for match in matches:
            disclosure_id = match.group(1)
            disclosure_text = match.group(2).strip()
            
            # Extract title (usually first line after disclosure ID)
            lines = disclosure_text.split('\n')
            title = lines[0].strip() if lines else f"Disclosure {disclosure_id}"
            description = disclosure_text[:500]  # First 500 chars as description
            
            clause_id = f"GRI_{standard_num}_{disclosure_id}".replace(" ", "_")
            
            # Determine evidence type based on keywords
            evidence_types = self._infer_evidence_types(disclosure_text)
            
            # Create validation rules
            validation_rules = self._create_gri_validation_rules(disclosure_text, clause_id)
            
            clause = ESGClause(
                clause_id=clause_id,
                framework=ESGFramework.GRI,
                section=topic,
                title=title[:200],  # Limit title length
                description=description,
                required_evidence_type=evidence_types,
                mandatory=True,
                validation_rules=validation_rules,
                keywords=self._extract_keywords(disclosure_text)
            )
            
            clauses.append(clause)
            clause_counter += 1
        
        # If no disclosures found, create at least one clause per document
        if not clauses:
            clause = self._create_fallback_clause(
                framework=ESGFramework.GRI,
                standard_num=standard_num,
                topic=topic,
                text=full_text[:1000]
            )
            clauses.append(clause)
        
        return clauses
    
    # ============= BRSR Parser =============
    
    def parse_brsr_standard(self) -> List[ESGClause]:
        """Parse BRSR (Business Responsibility and Sustainability Report)"""
        brsr_path = self.standards_dir / "BRSR.pdf"
        if not brsr_path.exists():
            logger.warning(f"BRSR file not found: {brsr_path}")
            return []
        
        doc = fitz.open(str(brsr_path))
        clauses = []
        
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        
        doc.close()
        
        # BRSR has Principles (A-I) and Essential/Leadership Indicators
        # Pattern: Section X or Principle X
        sections = self._split_brsr_sections(full_text)
        
        for section_name, section_text in sections:
            # Extract indicators from each section
            indicators = self._extract_brsr_indicators(section_text)
            
            for indicator_id, indicator_text in indicators:
                clause_id = f"BRSR_{section_name}_{indicator_id}".replace(" ", "_")
                
                evidence_types = self._infer_evidence_types(indicator_text)
                validation_rules = self._create_brsr_validation_rules(indicator_text, clause_id)
                
                clause = ESGClause(
                    clause_id=clause_id,
                    framework=ESGFramework.BRSR,
                    section=section_name,
                    title=indicator_id,
                    description=indicator_text[:500],
                    required_evidence_type=evidence_types,
                    mandatory=True,
                    validation_rules=validation_rules,
                    keywords=self._extract_keywords(indicator_text)
                )
                
                clauses.append(clause)
        
        logger.info(f"Parsed {len(clauses)} clauses from BRSR")
        return clauses
    
    def _split_brsr_sections(self, text: str) -> List[Tuple[str, str]]:
        """Split BRSR into major sections"""
        sections = []
        
        # Look for "SECTION" or "Principle" markers
        section_pattern = r'(SECTION [A-Z]|Principle \d+)[:\s]+(.*?)(?=SECTION [A-Z]|Principle \d+|$)'
        matches = re.finditer(section_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            section_name = match.group(1).strip()
            section_text = match.group(2).strip()
            sections.append((section_name, section_text))
        
        # If no sections found, treat entire document as one section
        if not sections:
            sections.append(("General", text))
        
        return sections
    
    def _extract_brsr_indicators(self, section_text: str) -> List[Tuple[str, str]]:
        """Extract indicators from BRSR section"""
        indicators = []
        
        # Pattern: "Essential Indicator X" or "Leadership Indicator Y"
        indicator_pattern = r'(Essential Indicator|Leadership Indicator)\s+(\S+)[:\s]+(.*?)(?=Essential Indicator|Leadership Indicator|$)'
        matches = re.finditer(indicator_pattern, section_text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            indicator_type = match.group(1)
            indicator_num = match.group(2)
            indicator_text = match.group(3).strip()
            
            indicator_id = f"{indicator_type}_{indicator_num}".replace(" ", "_")
            indicators.append((indicator_id, indicator_text))
        
        return indicators
    
    # ============= SASB Parser =============
    
    def parse_sasb_standard(self) -> List[ESGClause]:
        """Parse SASB (Sustainability Accounting Standards Board)"""
        sasb_path = self.standards_dir / "automobiles-standard_en-gb-sasb.pdf"
        if not sasb_path.exists():
            logger.warning(f"SASB file not found: {sasb_path}")
            return []
        
        doc = fitz.open(str(sasb_path))
        clauses = []
        
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        
        doc.close()
        
        # SASB has "Accounting Metrics" sections
        metrics = self._extract_sasb_metrics(full_text)
        
        for metric_id, metric_text in metrics:
            clause_id = f"SASB_{metric_id}".replace(" ", "_").replace(".", "_")
            
            evidence_types = self._infer_evidence_types(metric_text)
            validation_rules = self._create_sasb_validation_rules(metric_text, clause_id)
            
            clause = ESGClause(
                clause_id=clause_id,
                framework=ESGFramework.SASB,
                section="Automobiles",  # Sector-specific
                title=metric_id,
                description=metric_text[:500],
                required_evidence_type=evidence_types,
                mandatory=True,
                validation_rules=validation_rules,
                keywords=self._extract_keywords(metric_text)
            )
            
            clauses.append(clause)
        
        logger.info(f"Parsed {len(clauses)} clauses from SASB")
        return clauses
    
    def _extract_sasb_metrics(self, text: str) -> List[Tuple[str, str]]:
        """Extract SASB accounting metrics"""
        metrics = []
        
        # Pattern: "TR-AU-XXX-a" (SASB metric codes)
        metric_pattern = r'(TR-AU-\d+-[a-z])[:\s]+(.*?)(?=TR-AU-\d+-[a-z]|$)'
        matches = re.finditer(metric_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            metric_id = match.group(1)
            metric_text = match.group(2).strip()
            metrics.append((metric_id, metric_text))
        
        return metrics
    
    # ============= TCFD Parser =============
    
    def parse_tcfd_standard(self) -> List[ESGClause]:
        """Parse TCFD (Task Force on Climate-related Financial Disclosures)"""
        tcfd_path = self.standards_dir / "tcfd.pdf"
        if not tcfd_path.exists():
            logger.warning(f"TCFD file not found: {tcfd_path}")
            return []
        
        doc = fitz.open(str(tcfd_path))
        clauses = []
        
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        
        doc.close()
        
        # TCFD has 4 pillars: Governance, Strategy, Risk Management, Metrics & Targets
        pillars = self._extract_tcfd_pillars(full_text)
        
        for pillar_name, recommendations in pillars:
            for rec_id, rec_text in recommendations:
                clause_id = f"TCFD_{pillar_name}_{rec_id}".replace(" ", "_")
                
                evidence_types = self._infer_evidence_types(rec_text)
                validation_rules = self._create_tcfd_validation_rules(rec_text, clause_id)
                
                clause = ESGClause(
                    clause_id=clause_id,
                    framework=ESGFramework.TCFD,
                    section=pillar_name,
                    title=rec_id,
                    description=rec_text[:500],
                    required_evidence_type=evidence_types,
                    mandatory=True,
                    validation_rules=validation_rules,
                    keywords=self._extract_keywords(rec_text)
                )
                
                clauses.append(clause)
        
        logger.info(f"Parsed {len(clauses)} clauses from TCFD")
        return clauses
    
    def _extract_tcfd_pillars(self, text: str) -> List[Tuple[str, List[Tuple[str, str]]]]:
        """Extract TCFD pillars and recommendations"""
        pillars = [
            ("Governance", []),
            ("Strategy", []),
            ("Risk_Management", []),
            ("Metrics_and_Targets", [])
        ]
        
        # Look for recommendation patterns
        rec_pattern = r'Recommended Disclosure\s+([a-z]\))[:\s]+(.*?)(?=Recommended Disclosure|$)'
        matches = re.finditer(rec_pattern, text, re.DOTALL | re.IGNORECASE)
        
        current_pillar_idx = 0
        for match in matches:
            rec_id = match.group(1)
            rec_text = match.group(2).strip()
            
            # Determine which pillar based on keywords
            if any(kw in rec_text.lower() for kw in ['governance', 'board', 'management']):
                current_pillar_idx = 0
            elif any(kw in rec_text.lower() for kw in ['strategy', 'scenario', 'resilience']):
                current_pillar_idx = 1
            elif any(kw in rec_text.lower() for kw in ['risk', 'identify', 'assess']):
                current_pillar_idx = 2
            elif any(kw in rec_text.lower() for kw in ['metric', 'target', 'emission', 'ghg']):
                current_pillar_idx = 3
            
            pillars[current_pillar_idx][1].append((rec_id, rec_text))
        
        return pillars
    
    # ============= Helper Methods =============
    
    def _infer_evidence_types(self, text: str) -> List[EvidenceType]:
        """Infer required evidence types from clause text"""
        text_lower = text.lower()
        evidence_types = []
        
        # Numeric evidence
        if any(kw in text_lower for kw in ['amount', 'number', 'percentage', 'metric', 'ton', 'kwh', 'quantitative']):
            evidence_types.append(EvidenceType.NUMERIC)
        
        # Descriptive
        if any(kw in text_lower for kw in ['describe', 'explain', 'narrative', 'discussion', 'approach']):
            evidence_types.append(EvidenceType.DESCRIPTIVE)
        
        # Policy
        if any(kw in text_lower for kw in ['policy', 'procedure', 'governance', 'framework', 'commitment']):
            evidence_types.append(EvidenceType.POLICY)
        
        # Certification
        if any(kw in text_lower for kw in ['certification', 'certified', 'verified', 'audit', 'assurance']):
            evidence_types.append(EvidenceType.CERTIFICATION)
        
        # Timestamp
        if any(kw in text_lower for kw in ['date', 'period', 'year', 'reporting period', 'fiscal']):
            evidence_types.append(EvidenceType.TIMESTAMP)
        
        # Table
        if any(kw in text_lower for kw in ['table', 'breakdown', 'category', 'segmentation']):
            evidence_types.append(EvidenceType.TABLE)
        
        # Default to descriptive if nothing found
        if not evidence_types:
            evidence_types.append(EvidenceType.DESCRIPTIVE)
        
        return evidence_types
    
    def _create_gri_validation_rules(self, text: str, clause_id: str) -> List[ValidationRule]:
        """Create validation rules for GRI clauses"""
        rules = []
        text_lower = text.lower()
        
        # Numeric validation
        if 'total' in text_lower or 'amount' in text_lower:
            rules.append(ValidationRule(
                rule_id=f"{clause_id}_numeric",
                rule_type="numeric",
                description="Numeric value required",
                parameters={"min_value": 0},
                mandatory=True
            ))
        
        # Timestamp validation
        if 'reporting period' in text_lower or 'year' in text_lower:
            rules.append(ValidationRule(
                rule_id=f"{clause_id}_temporal",
                rule_type="temporal",
                description="Valid time period required",
                parameters={"format": "year"},
                mandatory=True
            ))
        
        return rules
    
    def _create_brsr_validation_rules(self, text: str, clause_id: str) -> List[ValidationRule]:
        """Create validation rules for BRSR clauses"""
        return self._create_gri_validation_rules(text, clause_id)  # Similar logic
    
    def _create_sasb_validation_rules(self, text: str, clause_id: str) -> List[ValidationRule]:
        """Create validation rules for SASB clauses"""
        return self._create_gri_validation_rules(text, clause_id)  # Similar logic
    
    def _create_tcfd_validation_rules(self, text: str, clause_id: str) -> List[ValidationRule]:
        """Create validation rules for TCFD clauses"""
        rules = []
        text_lower = text.lower()
        
        # Scenario analysis required for strategy
        if 'scenario' in text_lower:
            rules.append(ValidationRule(
                rule_id=f"{clause_id}_scenario",
                rule_type="keyword",
                description="Scenario analysis required",
                parameters={"keywords": ["scenario", "2°C", "climate scenario"]},
                mandatory=True
            ))
        
        return rules
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract relevant keywords from text"""
        # Simple keyword extraction based on frequency
        text_lower = text.lower()
        
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be'
        }
        
        words = re.findall(r'\b[a-z]{4,}\b', text_lower)
        words = [w for w in words if w not in stop_words]
        
        # Count frequency
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:max_keywords]]
        
        return keywords
    
    def _create_fallback_clause(
        self, 
        framework: ESGFramework,
        standard_num: str,
        topic: str,
        text: str
    ) -> ESGClause:
        """Create a fallback clause when parsing fails"""
        clause_id = f"{framework.value}_{standard_num}_General".replace(" ", "_")
        
        return ESGClause(
            clause_id=clause_id,
            framework=framework,
            section=topic,
            title=f"{framework.value} {standard_num} - {topic}",
            description=text,
            required_evidence_type=[EvidenceType.DESCRIPTIVE],
            mandatory=True,
            validation_rules=[],
            keywords=self._extract_keywords(text)
        )
