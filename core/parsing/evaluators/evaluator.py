from typing import List, Dict, Any, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment
from difflib import SequenceMatcher
import re

class Evaluator:
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
        Align entities using Hungarian algorithm.
        Returns list of (gt_item, pred_item) tuples. Unmatched items are paired with None.
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
            
        # Unmatched ground truth
        for i in range(len(ground_truth)):
            if i not in row_ind:
                aligned_pairs.append((ground_truth[i], None))
                
        # Unmatched predicted
        for j in range(len(predicted)):
            if j not in col_ind:
                aligned_pairs.append((None, predicted[j]))
                
        return aligned_pairs

    def evaluate_field(self, gt_val: Any, pred_val: Any, strategy: str = "exact") -> float:
        """
        Evaluate a single field based on strategy.
        Strategies: exact, substring, date, text_similarity
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
        Evaluate a whole section (e.g., 'work').
        config: {
            "key_fields": ["name", "position"],
            "fields": {
                "name": "substring",
                "startDate": "date",
                "summary": "text_similarity"
            }
        }
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
        metrics["precision"] = true_positives / total_pred if total_pred > 0 else 0.0
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
