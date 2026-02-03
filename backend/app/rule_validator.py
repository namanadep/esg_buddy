"""
ESGBuddy Rule-Based Validation Engine
Deterministic rule validation to augment LLM decisions
"""

import re
from typing import List, Dict, Any
from datetime import datetime
import logging

from app.models import (
    ValidationRule, 
    RuleValidationResult, 
    RetrievedEvidence
)

logger = logging.getLogger(__name__)


class RuleValidator:
    """Execute rule-based validation on evidence"""
    
    def validate_rules(
        self, 
        rules: List[ValidationRule],
        evidence: List[RetrievedEvidence]
    ) -> List[RuleValidationResult]:
        """
        Validate all rules against retrieved evidence
        
        Args:
            rules: List of validation rules to check
            evidence: Retrieved evidence chunks
        
        Returns:
            List of validation results
        """
        results = []
        
        # Combine all evidence text for validation
        combined_evidence = " ".join([e.text for e in evidence])
        
        for rule in rules:
            try:
                result = self._validate_single_rule(rule, combined_evidence, evidence)
                results.append(result)
            except Exception as e:
                logger.error(f"Error validating rule {rule.rule_id}: {e}")
                results.append(RuleValidationResult(
                    rule_id=rule.rule_id,
                    passed=False,
                    message=f"Rule validation error: {str(e)}",
                    triggered=False
                ))
        
        return results
    
    def _validate_single_rule(
        self, 
        rule: ValidationRule,
        combined_text: str,
        evidence: List[RetrievedEvidence]
    ) -> RuleValidationResult:
        """Validate a single rule"""
        
        if rule.rule_type == "numeric":
            return self._validate_numeric(rule, combined_text)
        
        elif rule.rule_type == "temporal":
            return self._validate_temporal(rule, combined_text)
        
        elif rule.rule_type == "keyword":
            return self._validate_keyword(rule, combined_text)
        
        elif rule.rule_type == "field_presence":
            return self._validate_field_presence(rule, combined_text)
        
        else:
            return RuleValidationResult(
                rule_id=rule.rule_id,
                passed=False,
                message=f"Unknown rule type: {rule.rule_type}",
                triggered=False
            )
    
    def _validate_numeric(
        self, 
        rule: ValidationRule, 
        text: str
    ) -> RuleValidationResult:
        """
        Validate numeric evidence
        
        Parameters:
            - min_value: Minimum acceptable value
            - max_value: Maximum acceptable value (optional)
            - unit: Expected unit (optional)
        """
        params = rule.parameters
        
        # Find numeric values in text
        numeric_pattern = r'[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?'
        numbers = re.findall(numeric_pattern, text)
        
        if not numbers:
            return RuleValidationResult(
                rule_id=rule.rule_id,
                passed=False,
                message="No numeric values found in evidence",
                triggered=True
            )
        
        # Check if any number meets criteria
        min_value = params.get("min_value", float('-inf'))
        max_value = params.get("max_value", float('inf'))
        
        valid_numbers = []
        for num_str in numbers:
            try:
                num = float(num_str)
                if min_value <= num <= max_value:
                    valid_numbers.append(num)
            except ValueError:
                continue
        
        if valid_numbers:
            return RuleValidationResult(
                rule_id=rule.rule_id,
                passed=True,
                message=f"Found valid numeric values: {valid_numbers[:3]}",
                triggered=True
            )
        else:
            return RuleValidationResult(
                rule_id=rule.rule_id,
                passed=False,
                message=f"No numeric values within range [{min_value}, {max_value}]",
                triggered=True
            )
    
    def _validate_temporal(
        self, 
        rule: ValidationRule, 
        text: str
    ) -> RuleValidationResult:
        """
        Validate time period references
        
        Parameters:
            - format: Expected format ("year", "date", "period")
            - min_year: Minimum year (optional)
            - max_year: Maximum year (optional)
        """
        params = rule.parameters
        format_type = params.get("format", "year")
        
        if format_type == "year":
            # Find 4-digit years
            year_pattern = r'\b(19|20)\d{2}\b'
            years = re.findall(year_pattern, text)
            
            if not years:
                return RuleValidationResult(
                    rule_id=rule.rule_id,
                    passed=False,
                    message="No year references found in evidence",
                    triggered=True
                )
            
            # Check year validity
            min_year = params.get("min_year", 1900)
            max_year = params.get("max_year", datetime.now().year)
            
            valid_years = [y for y in years if min_year <= int(y) <= max_year]
            
            if valid_years:
                return RuleValidationResult(
                    rule_id=rule.rule_id,
                    passed=True,
                    message=f"Found valid years: {valid_years[:5]}",
                    triggered=True
                )
            else:
                return RuleValidationResult(
                    rule_id=rule.rule_id,
                    passed=False,
                    message=f"No years within valid range [{min_year}, {max_year}]",
                    triggered=True
                )
        
        elif format_type == "date":
            # Look for date patterns
            date_patterns = [
                r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY
                r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',  # MM-DD-YYYY
                r'\b\d{4}-\d{1,2}-\d{1,2}\b'     # YYYY-MM-DD
            ]
            
            dates_found = []
            for pattern in date_patterns:
                dates_found.extend(re.findall(pattern, text))
            
            if dates_found:
                return RuleValidationResult(
                    rule_id=rule.rule_id,
                    passed=True,
                    message=f"Found dates: {dates_found[:3]}",
                    triggered=True
                )
            else:
                return RuleValidationResult(
                    rule_id=rule.rule_id,
                    passed=False,
                    message="No date references found",
                    triggered=True
                )
        
        else:
            # General period check
            period_keywords = ['period', 'fiscal year', 'quarter', 'reporting period']
            if any(kw in text.lower() for kw in period_keywords):
                return RuleValidationResult(
                    rule_id=rule.rule_id,
                    passed=True,
                    message="Time period reference found",
                    triggered=True
                )
            else:
                return RuleValidationResult(
                    rule_id=rule.rule_id,
                    passed=False,
                    message="No time period reference found",
                    triggered=True
                )
    
    def _validate_keyword(
        self, 
        rule: ValidationRule, 
        text: str
    ) -> RuleValidationResult:
        """
        Validate presence of specific keywords
        
        Parameters:
            - keywords: List of required keywords
            - match_all: Whether all keywords must be present (default: False)
        """
        params = rule.parameters
        keywords = params.get("keywords", [])
        match_all = params.get("match_all", False)
        
        if not keywords:
            return RuleValidationResult(
                rule_id=rule.rule_id,
                passed=False,
                message="No keywords specified in rule",
                triggered=False
            )
        
        text_lower = text.lower()
        found_keywords = [kw for kw in keywords if kw.lower() in text_lower]
        
        if match_all:
            passed = len(found_keywords) == len(keywords)
            message = f"Found {len(found_keywords)}/{len(keywords)} required keywords"
        else:
            passed = len(found_keywords) > 0
            message = f"Found keywords: {found_keywords[:5]}" if passed else "No matching keywords found"
        
        return RuleValidationResult(
            rule_id=rule.rule_id,
            passed=passed,
            message=message,
            triggered=True
        )
    
    def _validate_field_presence(
        self, 
        rule: ValidationRule, 
        text: str
    ) -> RuleValidationResult:
        """
        Validate presence of required fields
        
        Parameters:
            - fields: List of required field names/labels
        """
        params = rule.parameters
        fields = params.get("fields", [])
        
        if not fields:
            return RuleValidationResult(
                rule_id=rule.rule_id,
                passed=False,
                message="No fields specified in rule",
                triggered=False
            )
        
        text_lower = text.lower()
        found_fields = []
        
        for field in fields:
            # Look for field name followed by colon or similar
            field_pattern = rf'\b{re.escape(field.lower())}\s*[:=]'
            if re.search(field_pattern, text_lower):
                found_fields.append(field)
        
        passed = len(found_fields) == len(fields)
        
        if passed:
            message = f"All required fields present: {found_fields}"
        else:
            missing = set(fields) - set(found_fields)
            message = f"Missing required fields: {list(missing)}"
        
        return RuleValidationResult(
            rule_id=rule.rule_id,
            passed=passed,
            message=message,
            triggered=True
        )
