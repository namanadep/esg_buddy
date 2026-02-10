"""
ESGBuddy Enhanced ESG Clause Parser
LLM-powered intelligent parsing of ESG standards with fallback to regex
"""

import re
import time
import gc
import fitz  # PyMuPDF
from typing import List, Dict, Optional, Tuple, Any
import logging
from pathlib import Path
import json
import openai

from app.models import (
    ESGClause, 
    ESGFramework, 
    EvidenceType, 
    ValidationRule
)
from app.config import settings

logger = logging.getLogger(__name__)


class EnhancedClauseParser:
    """Enhanced parser with LLM-based intelligent extraction"""
    
    def __init__(self, use_llm: bool = True):
        self.standards_dir = Path(settings.standards_dir)
        self.use_llm = use_llm
        self.llm_client = None
        
        if use_llm:
            try:
                self.llm_client = openai.OpenAI(api_key=settings.openai_api_key)
                self.llm_model = settings.llm_model
            except Exception as e:
                logger.warning(f"LLM not available for parsing: {e}. Using regex fallback.")
                self.use_llm = False
    
    def parse_all_standards(self) -> List[ESGClause]:
        """Parse ESG standards from enabled frameworks only (see config.parse_frameworks)"""
        all_clauses = []
        
        # Only parse frameworks listed in config (e.g. "BRSR" for fast startup)
        enabled = [f.strip().upper() for f in settings.parse_frameworks.split(",") if f.strip()]
        if not enabled:
            enabled = ["BRSR"]  # default to BRSR only
        
        for framework in ESGFramework:
            if framework.value not in enabled:
                logger.info(f"Skipping {framework.value} (not in parse_frameworks)")
                continue
            framework_dir = self.standards_dir / framework.value
            
            if not framework_dir.exists():
                logger.warning(f"{framework.value} directory not found: {framework_dir}")
                continue
            
            logger.info(f"Parsing {framework.value} standards from {framework_dir}")
            
            # Find all PDFs recursively (dedupe: on Windows *.pdf and *.PDF match the same files)
            pdf_files = list({p.resolve() for p in framework_dir.rglob("*.pdf")} | {p.resolve() for p in framework_dir.rglob("*.PDF")})
            pdf_files = [Path(p) for p in sorted(str(x) for x in pdf_files)]
            logger.info(f"Found {len(pdf_files)} PDF files for {framework.value}")
            
            for pdf_path in pdf_files:
                try:
                    clauses = self._parse_standard_document(pdf_path, framework)
                    all_clauses.extend(clauses)
                    logger.info(f"Parsed {len(clauses)} clauses from {pdf_path.name}")
                except Exception as e:
                    logger.error(f"Error parsing {pdf_path.name}: {e}")
        
        logger.info(f"Total parsed: {len(all_clauses)} clauses from all standards")
        return all_clauses
    
    def parse_framework(self, framework: ESGFramework) -> List[ESGClause]:
        """Parse only one framework (e.g. for incremental add when others already in DB)."""
        all_clauses = []
        framework_dir = self.standards_dir / framework.value
        if not framework_dir.exists():
            logger.warning(f"{framework.value} directory not found: {framework_dir}")
            return []
        logger.info(f"Parsing {framework.value} standards from {framework_dir}")
        pdf_files = list({p.resolve() for p in framework_dir.rglob("*.pdf")} | {p.resolve() for p in framework_dir.rglob("*.PDF")})
        pdf_files = [Path(p) for p in sorted(str(x) for x in pdf_files)]
        logger.info(f"Found {len(pdf_files)} PDF files for {framework.value}")
        for pdf_path in pdf_files:
            try:
                clauses = self._parse_standard_document(pdf_path, framework)
                all_clauses.extend(clauses)
                logger.info(f"Parsed {len(clauses)} clauses from {pdf_path.name}")
                # Clear clauses list after extending to free memory
                del clauses
                gc.collect()
            except Exception as e:
                logger.error(f"Error parsing {pdf_path.name}: {e}")
        logger.info(f"Total parsed for {framework.value}: {len(all_clauses)} clauses")
        del pdf_files  # Clear PDF list
        return all_clauses
    
    def _parse_standard_document(
        self, 
        pdf_path: Path, 
        framework: ESGFramework
    ) -> List[ESGClause]:
        """
        Parse a single standard document using LLM or regex fallback
        """
        # Extract text from PDF
        text, page_count = self._extract_pdf_text(pdf_path)
        
        if not text or len(text.strip()) < 100:
            logger.warning(f"Insufficient text in {pdf_path.name}")
            return []
        
        # Try LLM-based parsing first (more accurate)
        if self.use_llm and self.llm_client:
            try:
                clauses = self._llm_parse_document(
                    text=text,
                    pdf_path=pdf_path,
                    framework=framework
                )
                if clauses:
                    return clauses
                logger.info(f"LLM parsing returned no clauses for {pdf_path.name}, trying regex...")
            except Exception as e:
                logger.warning(f"LLM parsing failed for {pdf_path.name}: {e}, falling back to regex")
        
        # Fallback to regex-based parsing
        return self._regex_parse_document(text, pdf_path, framework)
    
    def _extract_pdf_text(self, pdf_path: Path) -> Tuple[str, int]:
        """Extract clean text from PDF (memory-efficient: process page-by-page)"""
        try:
            doc = fitz.open(str(pdf_path))
            text_parts = []
            page_count = len(doc)
            
            # Process pages one at a time to reduce memory
            for page_num in range(page_count):
                page = doc[page_num]
                page_text = page.get_text("text")
                if page_text.strip():
                    text_parts.append(page_text)
                # Clear page object immediately
                del page
            
            doc.close()
            del doc
            gc.collect()  # Force garbage collection
            
            full_text = "\n\n".join(text_parts)
            del text_parts  # Clear list after joining
            return full_text, page_count
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return "", 0
    
    # ============= LLM-Based Parsing =============
    
    def _split_text_into_chunks(
        self,
        text: str,
        chunk_size: int = 40000,  # Reduced from 55k to 40k for memory safety
        overlap: int = 3000  # Reduced overlap for memory safety
    ) -> List[str]:
        """Split long text into overlapping chunks, breaking at paragraph boundaries when possible."""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []
        chunks = []
        start = 0
        prev_start = -1  # Track previous start to detect infinite loops
        max_iterations = len(text) // (chunk_size - overlap) + 10  # Fail-safe limit
        iteration = 0
        
        while start < len(text) and iteration < max_iterations:
            # Prevent infinite loop
            if start == prev_start:
                logger.error(f"Infinite loop detected in chunking at position {start}. Breaking.")
                break
            prev_start = start
            iteration += 1
            
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            # Prefer to end at a paragraph (double newline) to avoid cutting clauses
            if end < len(text) and len(chunk) > overlap:
                last_para = chunk.rfind("\n\n", len(chunk) // 2, len(chunk))
                if last_para > 0:
                    chunk = chunk[: last_para + 1]
                    end = start + len(chunk)
            chunks.append(chunk)
            
            # Ensure we always make progress
            new_start = end - overlap
            if new_start <= start:
                # If we're not making progress, force advancement
                new_start = start + max(1, chunk_size - overlap)
            start = new_start
            
            if start >= len(text):
                break
        
        if iteration >= max_iterations:
            logger.warning(f"Chunking hit iteration limit at {iteration}. May have incomplete chunks.")
        
        return chunks
    
    def _llm_parse_document(
        self,
        text: str,
        pdf_path: Path,
        framework: ESGFramework
    ) -> List[ESGClause]:
        """
        Use LLM to intelligently extract clauses from the standard document.
        Memory-optimized: process chunks one at a time and clear intermediate data.
        """
        max_chars_per_call = 45000  # Reduced from 60k to 45k for memory safety
        chunks = self._split_text_into_chunks(
            text,
            chunk_size=40000,  # Reduced from 55k to 40k
            overlap=3000  # Reduced from 5k to 3k for memory safety
        )
        if len(chunks) > 1:
            logger.info(
                f"Document long ({len(text)} chars), splitting into {len(chunks)} chunks for LLM parsing"
            )
        
        # Clear original text from memory after chunking
        del text
        gc.collect()
        
        all_clauses = []
        seen_ids = set()
        
        for i, chunk in enumerate(chunks):
            chunk_text = chunk[:max_chars_per_call] if len(chunk) > max_chars_per_call else chunk
            del chunk  # Clear chunk immediately after extracting text
            prompt = self._build_parsing_prompt(chunk_text, pdf_path, framework)
            del chunk_text  # Clear chunk text after building prompt
            
            try:
                response = self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are an expert at extracting structured compliance requirements from {framework.value} ESG standard documents."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=1,  # gpt-5-nano only supports default (1)
                    response_format={"type": "json_object"}
                )
                del prompt  # Clear prompt after API call
                
                result = json.loads(response.choices[0].message.content)
                del response  # Clear response immediately
                
                clauses = self._convert_llm_response_to_clauses(result, pdf_path, framework)
                del result  # Clear result after conversion
                
                for c in clauses:
                    # Deduplicate by clause_id across chunks
                    key = (c.clause_id, (c.title or "")[:80])
                    if key in seen_ids:
                        continue
                    seen_ids.add(key)
                    all_clauses.append(c)
                
                del clauses  # Clear clauses list after processing
                
                if len(chunks) > 1:
                    logger.info(f"Chunk {i + 1}/{len(chunks)}: extracted {len([k for k in seen_ids])} unique clauses so far")
                
                # Delay and garbage collection between chunks
                if i < len(chunks) - 1:
                    time.sleep(2.5)  # Increased to 2.5s for better memory recovery
                    gc.collect()
                    logger.info(f"Memory cleared, waiting before next chunk...")
                    
            except Exception as e:
                logger.warning(f"LLM parsing failed for chunk {i + 1}: {e}")
        
        del chunks  # Clear chunks list
        del seen_ids  # Clear seen_ids set
        gc.collect()
        
        logger.info(f"LLM extracted {len(all_clauses)} clauses from {pdf_path.name}")
        return all_clauses
    
    def _build_parsing_prompt(
        self, 
        text: str, 
        pdf_path: Path,
        framework: ESGFramework
    ) -> str:
        """Build prompt for LLM-based clause extraction"""
        
        filename = pdf_path.stem
        
        prompt = f"""Extract all compliance requirements/clauses from this {framework.value} standard document.

**Document:** {filename}
**Framework:** {framework.value}

**Document Text:**
{text[:60000]}... (truncated if needed)

**Task:**
Extract all compliance clauses, requirements, disclosures, or indicators. For each one, provide:

1. **clause_id**: Unique identifier (e.g., "GRI 305-1", "BRSR P1-E1", "SASB TR-AU-410a.1")
2. **title**: Short descriptive title
3. **description**: Full requirement text (what companies must disclose/report)
4. **section**: Section or topic name (e.g., "Emissions", "Governance")
5. **required_evidence_types**: Array of: "numeric", "descriptive", "policy", "certification", "timestamp", "table"
6. **mandatory**: true/false
7. **keywords**: Array of relevant keywords (5-10)

**Response Format (JSON):**
{{
    "clauses": [
        {{
            "clause_id": "...",
            "title": "...",
            "description": "...",
            "section": "...",
            "required_evidence_types": [...],
            "mandatory": true/false,
            "keywords": [...]
        }},
        ...
    ]
}}

Extract as many clauses as you can find. Be thorough and accurate. If the document has numbered disclosures, indicators, or metrics, extract each one separately.
"""
        
        return prompt
    
    def _convert_llm_response_to_clauses(
        self,
        llm_result: Dict[str, Any],
        pdf_path: Path,
        framework: ESGFramework
    ) -> List[ESGClause]:
        """Convert LLM JSON response to ESGClause objects"""
        clauses = []
        
        for idx, clause_data in enumerate(llm_result.get("clauses", [])):
            try:
                # Map evidence type strings to enums
                evidence_types = []
                for et_str in clause_data.get("required_evidence_types", ["descriptive"]):
                    try:
                        evidence_types.append(EvidenceType(et_str.lower()))
                    except ValueError:
                        evidence_types.append(EvidenceType.DESCRIPTIVE)
                
                if not evidence_types:
                    evidence_types = [EvidenceType.DESCRIPTIVE]
                
                # Create validation rules based on evidence types
                validation_rules = self._generate_validation_rules(
                    clause_id=clause_data.get("clause_id", f"clause_{idx}"),
                    evidence_types=evidence_types,
                    description=clause_data.get("description", "")
                )
                
                clause = ESGClause(
                    clause_id=clause_data.get("clause_id", f"{framework.value}_{idx}"),
                    framework=framework,
                    section=clause_data.get("section"),
                    title=clause_data.get("title", "Untitled"),
                    description=clause_data.get("description", ""),
                    required_evidence_type=evidence_types,
                    mandatory=clause_data.get("mandatory", True),
                    validation_rules=validation_rules,
                    keywords=clause_data.get("keywords", [])
                )
                
                clauses.append(clause)
                
            except Exception as e:
                logger.error(f"Error converting clause {idx} from LLM response: {e}")
        
        return clauses
    
    def _generate_validation_rules(
        self,
        clause_id: str,
        evidence_types: List[EvidenceType],
        description: str
    ) -> List[ValidationRule]:
        """Generate validation rules based on evidence types and description"""
        rules = []
        desc_lower = description.lower()
        
        # Numeric validation
        if EvidenceType.NUMERIC in evidence_types:
            rules.append(ValidationRule(
                rule_id=f"{clause_id}_numeric",
                rule_type="numeric",
                description="Numeric value required",
                parameters={"min_value": 0},
                mandatory=True
            ))
        
        # Temporal validation
        if EvidenceType.TIMESTAMP in evidence_types or any(kw in desc_lower for kw in ['year', 'period', 'date']):
            rules.append(ValidationRule(
                rule_id=f"{clause_id}_temporal",
                rule_type="temporal",
                description="Valid time period required",
                parameters={"format": "year"},
                mandatory=True
            ))
        
        # Keyword validation for policy documents
        if EvidenceType.POLICY in evidence_types:
            rules.append(ValidationRule(
                rule_id=f"{clause_id}_keyword_policy",
                rule_type="keyword",
                description="Policy-related keywords required",
                parameters={"keywords": ["policy", "procedure", "governance", "framework"]},
                mandatory=False
            ))
        
        return rules
    
    # ============= Regex-Based Parsing (Fallback) =============
    
    def _regex_parse_document(
        self,
        text: str,
        pdf_path: Path,
        framework: ESGFramework
    ) -> List[ESGClause]:
        """Regex-based parsing (fallback when LLM is unavailable or fails)"""
        
        if framework == ESGFramework.GRI:
            return self._regex_parse_gri(text, pdf_path)
        elif framework == ESGFramework.BRSR:
            return self._regex_parse_brsr(text, pdf_path)
        elif framework == ESGFramework.SASB:
            return self._regex_parse_sasb(text, pdf_path)
        elif framework == ESGFramework.TCFD:
            return self._regex_parse_tcfd(text, pdf_path)
        else:
            return []
    
    def _regex_parse_gri(self, text: str, pdf_path: Path) -> List[ESGClause]:
        """Regex parsing for GRI standards"""
        clauses = []
        filename = pdf_path.stem
        
        # Extract standard number
        standard_match = re.search(r'GRI (\d+[a-z]?)_', filename)
        standard_num = standard_match.group(1) if standard_match else "Unknown"
        
        # Extract topic
        topic = filename.split('_', 1)[1] if '_' in filename else "General"
        topic = re.sub(r'\s+\d{4}', '', topic).strip()
        
        # Pattern: "Disclosure XXX-Y" or "Disclosure XXX-Y-a"
        disclosure_pattern = r'Disclosure\s+(\d+-\d+(?:-[a-z])?)[:\s]+(.*?)(?=Disclosure\s+\d+-\d+|$)'
        matches = re.finditer(disclosure_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            disclosure_id = match.group(1)
            disclosure_text = match.group(2).strip()[:1000]
            
            lines = disclosure_text.split('\n')
            title = lines[0].strip()[:200] if lines else f"Disclosure {disclosure_id}"
            
            clause = ESGClause(
                clause_id=f"GRI_{standard_num}_{disclosure_id}".replace(" ", "_"),
                framework=ESGFramework.GRI,
                section=topic,
                title=title,
                description=disclosure_text[:800],
                required_evidence_type=self._infer_evidence_types(disclosure_text),
                mandatory=True,
                validation_rules=self._generate_validation_rules(
                    f"GRI_{standard_num}_{disclosure_id}",
                    self._infer_evidence_types(disclosure_text),
                    disclosure_text
                ),
                keywords=self._extract_keywords(disclosure_text)
            )
            clauses.append(clause)
        
        # Fallback if no disclosures found
        if not clauses:
            clauses.append(self._create_fallback_clause(
                framework=ESGFramework.GRI,
                standard_id=standard_num,
                topic=topic,
                text=text[:1000],
                pdf_path=pdf_path
            ))
        
        return clauses
    
    def _regex_parse_brsr(self, text: str, pdf_path: Path) -> List[ESGClause]:
        """
        Regex parsing for BRSR standards
        
        BRSR has different formats:
        - BRSR Core: Tabular format with Sr. No., Attribute, Parameter
        - Annexures: Section-based with Essential/Leadership Indicators
        """
        clauses = []
        filename = pdf_path.stem
        
        # Determine document type
        is_core = 'core' in filename.lower()
        is_annexure = 'annexure' in filename.lower()
        
        if is_core:
            # Parse BRSR Core (tabular format)
            clauses = self._parse_brsr_core_table(text, filename)
        elif is_annexure:
            # Parse BRSR Annexures (section/indicator format)
            clauses = self._parse_brsr_annexure(text, filename)
        else:
            # Try both approaches
            core_clauses = self._parse_brsr_core_table(text, filename)
            annexure_clauses = self._parse_brsr_annexure(text, filename)
            clauses = core_clauses if len(core_clauses) > len(annexure_clauses) else annexure_clauses
        
        # Fallback
        if not clauses:
            clauses.append(self._create_fallback_clause(
                framework=ESGFramework.BRSR,
                standard_id=filename,
                topic="General",
                text=text[:1000],
                pdf_path=pdf_path
            ))
        
        return clauses
    
    def _parse_brsr_core_table(self, text: str, filename: str) -> List[ESGClause]:
        """
        Parse BRSR Core table format
        
        BRSR Core has 9 core ESG metrics in a table format.
        Due to PDF table extraction challenges, we use known core metrics.
        """
        clauses = []
        
        # BRSR Core has 9 standardized metrics (as per SEBI)
        core_metrics = [
            {
                "sr_no": "1",
                "attribute": "Green-house gas (GHG) footprint",
                "keywords": ["scope 1", "scope 2", "scope 3", "ghg", "emissions", "carbon", "co2"]
            },
            {
                "sr_no": "2",
                "attribute": "Water footprint",
                "keywords": ["water", "consumption", "withdrawal", "discharge", "recycled"]
            },
            {
                "sr_no": "3",
                "attribute": "Waste footprint",
                "keywords": ["waste", "hazardous", "non-hazardous", "recycled", "disposal"]
            },
            {
                "sr_no": "4",
                "attribute": "Energy footprint",
                "keywords": ["energy", "consumption", "renewable", "non-renewable", "kwh"]
            },
            {
                "sr_no": "5",
                "attribute": "Employment metrics",
                "keywords": ["employees", "permanent", "contract", "women", "workers"]
            },
            {
                "sr_no": "6",
                "attribute": "Gender diversity",
                "keywords": ["women", "board", "management", "diversity", "female"]
            },
            {
                "sr_no": "7",
                "attribute": "Return to investors",
                "keywords": ["dividend", "buyback", "returns", "shareholders"]
            },
            {
                "sr_no": "8",
                "attribute": "Median remuneration",
                "keywords": ["compensation", "salary", "remuneration", "pay", "ceo"]
            },
            {
                "sr_no": "9",
                "attribute": "Turnover rate",
                "keywords": ["attrition", "turnover", "retention", "permanent", "workers"]
            }
        ]
        
        for metric in core_metrics:
            # Search for this metric in the text
            metric_pattern = re.compile(
                rf"{metric['sr_no']}.*?" + 
                rf"{re.escape(metric['attribute'][:15])}.*?" +
                r"(.{100,2000}?)" +
                r"(?=\d+\s+[A-Z]|$)",
                re.DOTALL | re.IGNORECASE
            )
            
            match = metric_pattern.search(text)
            
            if match:
                context = match.group(1).strip()
            else:
                # If not found, use keywords to find relevant section
                keyword_matches = []
                for keyword in metric['keywords']:
                    pattern = re.compile(rf'.{{0,300}}{re.escape(keyword)}.{{0,700}}', re.IGNORECASE)
                    keyword_matches.extend(pattern.findall(text))
                
                context = " ".join(keyword_matches[:3]) if keyword_matches else "No details found"
            
            clause_id = f"BRSR_Core_{metric['sr_no']}_{metric['attribute'][:40]}".replace(" ", "_").replace("(", "").replace(")", "")
            
            description = f"{metric['attribute']}\n\n{context[:800]}"
            
            clause = ESGClause(
                clause_id=clause_id,
                framework=ESGFramework.BRSR,
                section="BRSR Core",
                title=f"{metric['sr_no']}. {metric['attribute']}",
                description=description,
                required_evidence_type=self._infer_evidence_types(description),
                mandatory=True,
                validation_rules=self._generate_validation_rules(
                    clause_id,
                    self._infer_evidence_types(description),
                    description
                ),
                keywords=metric['keywords'][:8]
            )
            clauses.append(clause)
        
        return clauses
    
    def _parse_brsr_annexure(self, text: str, filename: str) -> List[ESGClause]:
        """
        Parse BRSR Annexure format
        
        Annexures have:
        - SECTION A: General disclosures (numbered questions)
        - SECTION B: Management & process disclosures (principles with indicators)
        - SECTION C: Principle-wise performance disclosure (detailed indicators)
        """
        clauses = []
        
        # Split by sections
        section_pattern = r'SECTION ([A-C])[:\s]*([^\n]+?)(?=SECTION [A-C]|$)'
        sections = re.finditer(section_pattern, text, re.DOTALL | re.IGNORECASE)
        
        section_data = [(m.group(1), m.group(2), m.start(), m.end()) for m in sections]
        
        # If no sections found, try to extract the full text as chunks
        if not section_data:
            section_data = [("General", text, 0, len(text))]
        
        for section_id, section_title, start, end in section_data:
            # Get section text
            if len(section_data) > 1:
                next_start = [s[2] for s in section_data if s[2] > start]
                section_end = next_start[0] if next_start else len(text)
                section_text = text[start:section_end]
            else:
                section_text = text
            
            section_name = f"SECTION {section_id}" if section_id != "General" else "General"
            
            # Extract numbered questions (for Section A and general numbered items)
            question_pattern = r'^(\d+)\.\s+(.+?)(?=^\d+\.|$)'
            questions = re.finditer(question_pattern, section_text, re.MULTILINE | re.DOTALL)
            
            for match in questions:
                q_num = match.group(1)
                q_text = match.group(2).strip()[:1200]
                
                # Extract first line as title
                lines = q_text.split('\n')
                title = lines[0].strip()[:200] if lines else f"Question {q_num}"
                
                clause_id = f"BRSR_{section_name}_Q{q_num}".replace(" ", "_")
                
                clause = ESGClause(
                    clause_id=clause_id,
                    framework=ESGFramework.BRSR,
                    section=section_name,
                    title=f"{q_num}. {title}",
                    description=q_text[:800],
                    required_evidence_type=self._infer_evidence_types(q_text),
                    mandatory=True,
                    validation_rules=self._generate_validation_rules(
                        clause_id,
                        self._infer_evidence_types(q_text),
                        q_text
                    ),
                    keywords=self._extract_keywords(q_text)
                )
                clauses.append(clause)
            
            # Also extract Essential/Leadership Indicators (for Sections B/C)
            indicator_pattern = r'(Essential Indicator|Leadership Indicator)\s+([A-Z0-9\-\.]+)[:\s]+(.*?)(?=Essential Indicator|Leadership Indicator|^\d+\.|$)'
            indicators = re.finditer(indicator_pattern, section_text, re.DOTALL | re.IGNORECASE)
            
            for match in indicators:
                indicator_type = match.group(1)
                indicator_id = match.group(2)
                indicator_text = match.group(3).strip()[:1200]
                
                clause_id = f"BRSR_{section_name}_{indicator_type}_{indicator_id}".replace(" ", "_")
                
                clause = ESGClause(
                    clause_id=clause_id,
                    framework=ESGFramework.BRSR,
                    section=section_name,
                    title=f"{indicator_type} {indicator_id}",
                    description=indicator_text[:800],
                    required_evidence_type=self._infer_evidence_types(indicator_text),
                    mandatory=True,
                    validation_rules=self._generate_validation_rules(
                        clause_id,
                        self._infer_evidence_types(indicator_text),
                        indicator_text
                    ),
                    keywords=self._extract_keywords(indicator_text)
                )
                clauses.append(clause)
        
        return clauses
    
    def _regex_parse_sasb(self, text: str, pdf_path: Path) -> List[ESGClause]:
        """Regex parsing for SASB standards"""
        clauses = []
        
        # Extract sector from path (e.g., Consumer Goods/apparel-...)
        sector = pdf_path.parent.name if pdf_path.parent.name != "SASB" else "General"
        filename = pdf_path.stem
        
        # SASB metric codes: sector-specific like TR-AU-XXX-a, CG-AA-XXX-a, etc.
        # General pattern: XX-XX-XXX-a
        metric_pattern = r'([A-Z]{2}-[A-Z]{2}-\d{3}-[a-z])[:\s\.]+(.*?)(?=[A-Z]{2}-[A-Z]{2}-\d{3}-[a-z]|$)'
        matches = re.finditer(metric_pattern, text, re.DOTALL)
        
        for match in matches:
            metric_id = match.group(1)
            metric_text = match.group(2).strip()[:1000]
            
            clause = ESGClause(
                clause_id=f"SASB_{metric_id}".replace("-", "_"),
                framework=ESGFramework.SASB,
                section=sector,
                title=metric_id,
                description=metric_text[:800],
                required_evidence_type=self._infer_evidence_types(metric_text),
                mandatory=True,
                validation_rules=self._generate_validation_rules(
                    f"SASB_{metric_id}",
                    self._infer_evidence_types(metric_text),
                    metric_text
                ),
                keywords=self._extract_keywords(metric_text)
            )
            clauses.append(clause)
        
        # Fallback
        if not clauses:
            clauses.append(self._create_fallback_clause(
                framework=ESGFramework.SASB,
                standard_id=sector,
                topic=filename,
                text=text[:1000],
                pdf_path=pdf_path
            ))
        
        return clauses
    
    def _regex_parse_tcfd(self, text: str, pdf_path: Path) -> List[ESGClause]:
        """Regex parsing for TCFD standards"""
        clauses = []
        filename = pdf_path.stem
        
        # TCFD has "Recommended Disclosure" with letter labels (a, b, c, etc.)
        rec_pattern = r'Recommended Disclosure\s+([a-z]\))[:\s]+(.*?)(?=Recommended Disclosure|$)'
        matches = re.finditer(rec_pattern, text, re.DOTALL | re.IGNORECASE)
        
        # Determine pillar from context
        pillars = ["Governance", "Strategy", "Risk_Management", "Metrics_and_Targets"]
        current_pillar = "General"
        
        for match in matches:
            rec_id = match.group(1)
            rec_text = match.group(2).strip()[:1000]
            
            # Infer pillar
            if any(kw in rec_text.lower() for kw in ['governance', 'board', 'oversight']):
                current_pillar = "Governance"
            elif any(kw in rec_text.lower() for kw in ['strategy', 'scenario', 'resilience']):
                current_pillar = "Strategy"
            elif any(kw in rec_text.lower() for kw in ['risk', 'identify', 'assess', 'manage']):
                current_pillar = "Risk_Management"
            elif any(kw in rec_text.lower() for kw in ['metric', 'target', 'emission', 'ghg']):
                current_pillar = "Metrics_and_Targets"
            
            clause = ESGClause(
                clause_id=f"TCFD_{current_pillar}_{rec_id}".replace(" ", "_").replace(")", ""),
                framework=ESGFramework.TCFD,
                section=current_pillar.replace("_", " "),
                title=f"Recommended Disclosure {rec_id}",
                description=rec_text[:800],
                required_evidence_type=self._infer_evidence_types(rec_text),
                mandatory=True,
                validation_rules=self._generate_validation_rules(
                    f"TCFD_{current_pillar}_{rec_id}",
                    self._infer_evidence_types(rec_text),
                    rec_text
                ),
                keywords=self._extract_keywords(rec_text)
            )
            clauses.append(clause)
        
        # Fallback
        if not clauses:
            clauses.append(self._create_fallback_clause(
                framework=ESGFramework.TCFD,
                standard_id=filename,
                topic="Climate Disclosure",
                text=text[:1000],
                pdf_path=pdf_path
            ))
        
        return clauses
    
    # ============= Helper Methods =============
    
    def _infer_evidence_types(self, text: str) -> List[EvidenceType]:
        """Infer required evidence types from text"""
        text_lower = text.lower()
        evidence_types = []
        
        if any(kw in text_lower for kw in ['amount', 'number', 'percentage', 'metric', 'ton', 'quantitative']):
            evidence_types.append(EvidenceType.NUMERIC)
        if any(kw in text_lower for kw in ['describe', 'explain', 'narrative', 'approach']):
            evidence_types.append(EvidenceType.DESCRIPTIVE)
        if any(kw in text_lower for kw in ['policy', 'procedure', 'governance', 'commitment']):
            evidence_types.append(EvidenceType.POLICY)
        if any(kw in text_lower for kw in ['certification', 'verified', 'audit', 'assurance']):
            evidence_types.append(EvidenceType.CERTIFICATION)
        if any(kw in text_lower for kw in ['date', 'period', 'year', 'fiscal']):
            evidence_types.append(EvidenceType.TIMESTAMP)
        if any(kw in text_lower for kw in ['table', 'breakdown', 'category']):
            evidence_types.append(EvidenceType.TABLE)
        
        return evidence_types if evidence_types else [EvidenceType.DESCRIPTIVE]
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract relevant keywords"""
        text_lower = text.lower()
        
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'this', 'that', 'it', 'its', 'which', 'their', 'should', 'must'
        }
        
        words = re.findall(r'\b[a-z]{4,}\b', text_lower)
        words = [w for w in words if w not in stop_words]
        
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]
    
    def _create_fallback_clause(
        self,
        framework: ESGFramework,
        standard_id: str,
        topic: str,
        text: str,
        pdf_path: Path
    ) -> ESGClause:
        """Create a fallback clause when parsing yields no results"""
        clause_id = f"{framework.value}_{standard_id}_{pdf_path.stem}".replace(" ", "_")[:100]
        
        return ESGClause(
            clause_id=clause_id,
            framework=framework,
            section=topic,
            title=f"{framework.value} - {topic}",
            description=text[:800],
            required_evidence_type=[EvidenceType.DESCRIPTIVE],
            mandatory=True,
            validation_rules=[],
            keywords=self._extract_keywords(text)
        )
