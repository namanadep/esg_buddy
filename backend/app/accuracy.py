"""
ESGBuddy Accuracy Measurement Module
Measures system accuracy against ground truth labels
"""

from typing import List, Dict, Any, Tuple
import logging
from datetime import datetime
from collections import defaultdict

from app.models import (
    ClauseEvaluation,
    GroundTruthLabel,
    AccuracyMetrics,
    ComplianceStatus,
    RetrievedEvidence
)

logger = logging.getLogger(__name__)


class AccuracyEvaluator:
    """Evaluate system accuracy against ground truth"""
    
    def __init__(self):
        self.ground_truth: Dict[str, GroundTruthLabel] = {}
    
    def add_ground_truth(self, labels: List[GroundTruthLabel]):
        """Add ground truth labels for benchmarking"""
        for label in labels:
            key = f"{label.document_id}_{label.clause_id}"
            self.ground_truth[key] = label
        
        logger.info(f"Added {len(labels)} ground truth labels")
    
    def evaluate_accuracy(
        self,
        evaluations: List[ClauseEvaluation],
        document_id: str
    ) -> AccuracyMetrics:
        """
        Calculate accuracy metrics for a set of evaluations
        
        Args:
            evaluations: List of clause evaluations from the system
            document_id: Document ID for these evaluations
        
        Returns:
            Accuracy metrics
        """
        logger.info(f"Calculating accuracy metrics for {len(evaluations)} evaluations")
        
        # Filter evaluations that have ground truth
        eval_with_truth = []
        for eval in evaluations:
            key = f"{document_id}_{eval.clause_id}"
            if key in self.ground_truth:
                eval_with_truth.append((eval, self.ground_truth[key]))
        
        if not eval_with_truth:
            logger.warning("No ground truth labels found for these evaluations")
            return self._create_zero_metrics(len(evaluations))
        
        # Calculate metrics
        retrieval_recall = self._calculate_retrieval_recall(eval_with_truth)
        llm_precision, llm_recall, llm_f1 = self._calculate_llm_metrics(eval_with_truth)
        rule_precision = self._calculate_rule_precision(eval_with_truth)
        confidence_calibration = self._calculate_confidence_calibration(eval_with_truth)
        
        metrics = AccuracyMetrics(
            retrieval_recall_at_k=retrieval_recall,
            llm_precision=llm_precision,
            llm_recall=llm_recall,
            llm_f1_score=llm_f1,
            rule_validation_precision=rule_precision,
            confidence_calibration_error=confidence_calibration,
            total_clauses_evaluated=len(eval_with_truth)
        )
        
        logger.info(f"Accuracy metrics: {metrics.model_dump()}")
        
        return metrics
    
    def _calculate_retrieval_recall(
        self,
        eval_with_truth: List[Tuple[ClauseEvaluation, GroundTruthLabel]]
    ) -> float:
        """
        Calculate Recall@K for retrieval
        
        Measures: % of clauses where at least one correct evidence page was retrieved
        """
        correct_retrievals = 0
        
        for evaluation, ground_truth in eval_with_truth:
            retrieved_pages = {ev.page_number for ev in evaluation.retrieved_evidence}
            expected_pages = set(ground_truth.expected_evidence_pages)
            
            # Check if any expected page was retrieved
            if retrieved_pages & expected_pages:
                correct_retrievals += 1
        
        recall = correct_retrievals / len(eval_with_truth) if eval_with_truth else 0.0
        return recall
    
    def _calculate_llm_metrics(
        self,
        eval_with_truth: List[Tuple[ClauseEvaluation, GroundTruthLabel]]
    ) -> Tuple[float, float, float]:
        """
        Calculate Precision, Recall, and F1 for LLM decisions
        
        Returns:
            (precision, recall, f1_score)
        """
        # Convert status to binary: compliant (supported/inferred) vs non-compliant
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        true_negatives = 0
        
        for evaluation, ground_truth in eval_with_truth:
            predicted_compliant = evaluation.final_status in [
                ComplianceStatus.SUPPORTED,
                ComplianceStatus.INFERRED
            ]
            expected_compliant = ground_truth.expected_status in [
                ComplianceStatus.SUPPORTED,
                ComplianceStatus.INFERRED
            ]
            
            if predicted_compliant and expected_compliant:
                true_positives += 1
            elif predicted_compliant and not expected_compliant:
                false_positives += 1
            elif not predicted_compliant and expected_compliant:
                false_negatives += 1
            else:
                true_negatives += 1
        
        # Calculate metrics
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return precision, recall, f1
    
    def _calculate_rule_precision(
        self,
        eval_with_truth: List[Tuple[ClauseEvaluation, GroundTruthLabel]]
    ) -> float:
        """
        Calculate precision of rule-based validation
        
        Measures: When rules override LLM, how often are they correct?
        """
        rule_overrides = []
        
        for evaluation, ground_truth in eval_with_truth:
            if evaluation.override_applied:
                # Check if the override was correct
                correct = evaluation.final_status == ground_truth.expected_status
                rule_overrides.append(correct)
        
        if not rule_overrides:
            return 1.0  # No overrides means no errors
        
        precision = sum(rule_overrides) / len(rule_overrides)
        return precision
    
    def _calculate_confidence_calibration(
        self,
        eval_with_truth: List[Tuple[ClauseEvaluation, GroundTruthLabel]]
    ) -> float:
        """
        Calculate confidence calibration error
        
        Measures correlation between confidence score and actual accuracy
        Lower is better (0 = perfect calibration)
        """
        # Group predictions by confidence bins
        bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        bin_data = defaultdict(list)
        
        for evaluation, ground_truth in eval_with_truth:
            confidence = evaluation.final_confidence
            correct = evaluation.final_status == ground_truth.expected_status
            
            # Find bin
            for i in range(len(bins) - 1):
                if bins[i] <= confidence < bins[i + 1]:
                    bin_data[i].append(correct)
                    break
        
        # Calculate calibration error
        calibration_error = 0.0
        total_samples = 0
        
        for bin_idx, correct_list in bin_data.items():
            if correct_list:
                avg_confidence = (bins[bin_idx] + bins[bin_idx + 1]) / 2
                accuracy = sum(correct_list) / len(correct_list)
                error = abs(avg_confidence - accuracy)
                
                calibration_error += error * len(correct_list)
                total_samples += len(correct_list)
        
        if total_samples > 0:
            calibration_error /= total_samples
        
        return calibration_error
    
    def _create_zero_metrics(self, total_clauses: int) -> AccuracyMetrics:
        """Create zero metrics when no ground truth available"""
        return AccuracyMetrics(
            retrieval_recall_at_k=0.0,
            llm_precision=0.0,
            llm_recall=0.0,
            llm_f1_score=0.0,
            rule_validation_precision=0.0,
            confidence_calibration_error=1.0,
            total_clauses_evaluated=total_clauses
        )
    
    def generate_self_benchmark(
        self,
        evaluations: List[ClauseEvaluation]
    ) -> Dict[str, Any]:
        """
        Generate self-benchmarking metrics when no ground truth is available
        
        Useful for system monitoring and quality checks
        """
        if not evaluations:
            return {}
        
        # Confidence distribution
        confidences = [e.final_confidence for e in evaluations]
        avg_confidence = sum(confidences) / len(confidences)
        low_confidence_count = sum(1 for c in confidences if c < 0.5)
        
        # Evidence quality
        avg_evidence_count = sum(len(e.retrieved_evidence) for e in evaluations) / len(evaluations)
        avg_similarity = sum(
            sum(ev.similarity_score for ev in e.retrieved_evidence) / len(e.retrieved_evidence)
            if e.retrieved_evidence else 0.0
            for e in evaluations
        ) / len(evaluations)
        
        # Rule validation stats
        total_rules_checked = sum(len(e.rule_results) for e in evaluations)
        rules_passed = sum(
            sum(1 for r in e.rule_results if r.passed)
            for e in evaluations
        )
        
        # Status distribution
        status_dist = defaultdict(int)
        for e in evaluations:
            status_dist[e.final_status.value] += 1
        
        return {
            "total_clauses": len(evaluations),
            "average_confidence": avg_confidence,
            "low_confidence_count": low_confidence_count,
            "average_evidence_retrieved": avg_evidence_count,
            "average_similarity_score": avg_similarity,
            "total_rules_checked": total_rules_checked,
            "rules_passed": rules_passed,
            "rule_pass_rate": rules_passed / total_rules_checked if total_rules_checked > 0 else 0.0,
            "status_distribution": dict(status_dist),
            "overrides_applied": sum(1 for e in evaluations if e.override_applied)
        }
