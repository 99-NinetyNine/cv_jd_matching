from typing import List, Dict, Any, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment
from difflib import SequenceMatcher
import re
from core.parsing.evaluators.base import BaseEvaluator

class HungarianEvaluator(BaseEvaluator):
    """ This is based on https://arxiv.org/pdf/2510.09722 """
    def __init__(self):
        pass

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate normalized string similarity (0.0 to 1.0).
        """
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str(str1).lower(), str(str2).lower()).ratio()

    def _compute_similarity_matrix(self, ground_truth: List[Dict], predicted: List[Dict], key_fields: List[str]) -> np.ndarray:
        """
        Compute similarity matrix between two lists of entities based on key fields.
        """
        m = len(ground_truth)
        n = len(predicted)
        matrix = np.zeros((m, n))
        
        for i, gt_item in enumerate(ground_truth):
            for j, pred_item in enumerate(predicted):
                # Average similarity of key fields
                scores = []
                for field in key_fields:
                    gt_val = gt_item.get(field, "")
                    pred_val = pred_item.get(field, "")
                    scores.append(self._calculate_similarity(gt_val, pred_val))
                
                matrix[i, j] = sum(scores) / len(scores) if scores else 0.0
                
        return matrix

    def align_entities(self, ground_truth: List[Dict], predicted: List[Dict], key_fields: List[str]) -> List[Tuple[Dict, Dict]]:
        """
        Stage 1: Entity Alignment via the Hungarian Algorithm.
        
        Challenges addressed:
        - Quantity mismatch: Handles different numbers of GT vs Predicted entities.
        - Order mismatch: Matches based on content similarity, not list index.
        - Partial match: Finds optimal assignment even if fields are imperfect.
        
        Method:
        1. Construct a Similarity Matrix (M x N) where each element is the average 
           normalized string similarity of 'key_fields' (e.g., company name, position).
        2. Apply the Hungarian Algorithm (linear_sum_assignment) to find the 
           one-to-one assignment that maximizes total similarity.
           
        Returns:
            List of (gt_item, pred_item) tuples. 
            - Unmatched ground truth items are paired with None: (gt, None) -> Missed extraction
            - Unmatched predicted items are paired with None: (None, pred) -> Spurious extraction
        """
        if not ground_truth and not predicted:
            return []
        
        if not ground_truth:
            return [(None, p) for p in predicted]
        
        if not predicted:
            return [(g, None) for g in ground_truth]

        # Cost matrix is negative similarity (Hungarian minimizes cost)
        sim_matrix = self._compute_similarity_matrix(ground_truth, predicted, key_fields)
        cost_matrix = -sim_matrix
        
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        aligned_pairs = []
        
        # Matched pairs
        for r, c in zip(row_ind, col_ind):
            aligned_pairs.append((ground_truth[r], predicted[c]))
            
        # Unmatched ground truth (Missed)
        for i in range(len(ground_truth)):
            if i not in row_ind:
                aligned_pairs.append((ground_truth[i], None))
                
        # Unmatched predicted (Spurious)
        for j in range(len(predicted)):
            if j not in col_ind:
                aligned_pairs.append((None, predicted[j]))
                
        return aligned_pairs

    def evaluate_field(self, gt_val: Any, pred_val: Any, strategy: str = "exact") -> float:
        """
        Stage 2: Multi-Strategy Field Matching.
        
        Recognizing that a single "exact match" rule is inadequate, this method 
        dynamically selects validation rules based on the field's semantic nature.
        
        Strategies:
        - 'date': Period Fields. Normalized (e.g., to YYYY-MM) for flexible matching.
        - 'substring': Named Entities (e.g., Company, Job Title). Tolerates abbreviations/suffixes.
        - 'text_similarity': Long Descriptions. Uses edit-distance/SequenceMatcher for paraphrasing.
        - 'exact': Other fields. Normalized exact match (lowercase, stripped).
        """
        if gt_val is None: gt_val = ""
        if pred_val is None: pred_val = ""
        
        gt_str = str(gt_val).strip()
        pred_str = str(pred_val).strip()
        
        if not gt_str and not pred_str:
            return 1.0
        if not gt_str or not pred_str:
            return 0.0
            
        if strategy == "exact":
            return 1.0 if gt_str.lower() == pred_str.lower() else 0.0
            
        elif strategy == "substring":
            return 1.0 if gt_str.lower() in pred_str.lower() or pred_str.lower() in gt_str.lower() else 0.0
            
        elif strategy == "text_similarity":
            return self._calculate_similarity(gt_str, pred_str)
            
        elif strategy == "date":
            # Simple date normalization (YYYY-MM)
            # This is a placeholder for more complex date parsing
            return 1.0 if gt_str[:7] == pred_str[:7] else 0.0
            
        return 0.0

    def evaluate_section(self, ground_truth: List[Dict], predicted: List[Dict], config: Dict) -> Dict:
        """
        Orchestrates the Two-Stage Evaluation for a specific section (e.g., 'work').
        
        1. Aligns entities using Hungarian Algorithm.
        2. Performs fine-grained field comparison on aligned pairs.
        3. Aggregates results into Precision, Recall, and F1.
        """
        key_fields = config.get("key_fields", [])
        aligned_pairs = self.align_entities(ground_truth, predicted, key_fields)
        
        metrics = {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "field_scores": {}
        }
        
        total_gt = len(ground_truth)
        total_pred = len(predicted)
        true_positives = 0
        
        field_totals = {f: 0 for f in config["fields"]}
        field_corrects = {f: 0.0 for f in config["fields"]}
        
        for gt, pred in aligned_pairs:
            if gt and pred:
                # Check if it's a "match" based on key fields threshold
                # For now, assume Hungarian assignment is the match
                true_positives += 1
                
                # Field level evaluation
                for field, strategy in config["fields"].items():
                    gt_val = gt.get(field)
                    pred_val = pred.get(field)
                    score = self.evaluate_field(gt_val, pred_val, strategy)
                    field_corrects[field] += score
                    field_totals[field] += 1
        
        # Calculate metrics
        # Precision = TP / (TP + FP) = TP / Total Predicted
        metrics["precision"] = true_positives / total_pred if total_pred > 0 else 0.0
        
        # Recall = TP / (TP + FN) = TP / Total Ground Truth
        metrics["recall"] = true_positives / total_gt if total_gt > 0 else 0.0
        
        if metrics["precision"] + metrics["recall"] > 0:
            metrics["f1"] = 2 * (metrics["precision"] * metrics["recall"]) / (metrics["precision"] + metrics["recall"])
            
        for field in config["fields"]:
            total = field_totals[field]
            if total > 0:
                metrics["field_scores"][field] = field_corrects[field] / total
            else:
                metrics["field_scores"][field] = 0.0
                
        return metrics
