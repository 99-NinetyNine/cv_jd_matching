from typing import Dict
from core.parsing.evaluators.evaluator import HungarianEvaluator

class FullResumeEvaluator(HungarianEvaluator):
    """
    Extension of HungarianEvaluator to support full resume evaluation across all sections.
    """
    
    def evaluate_basics(self, gt_basics: Dict, pred_basics: Dict) -> Dict:
        """
        Evaluate the 'basics' section (single object, not a list).
        """
        if not gt_basics and not pred_basics:
            return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "field_scores": {}}
            
        gt_basics = gt_basics or {}
        pred_basics = pred_basics or {}
        
        fields = ["name", "label", "email", "phone", "url", "summary"]
        field_scores = {}
        
        for field in fields:
            gt_val = gt_basics.get(field)
            pred_val = pred_basics.get(field)
            
            strategy = "exact" if field in ["email", "url"] else "text_similarity"
            score = self.evaluate_field(gt_val, pred_val, strategy)
            field_scores[field] = score
            
        # For basics, use average field score as quality metric
        avg_score = sum(field_scores.values()) / len(field_scores) if field_scores else 0.0
        
        return {
            "precision": 1.0,  # Simplified for single object
            "recall": 1.0,
            "f1": avg_score,  # Use avg field score as proxy for quality
            "field_scores": field_scores
        }

    def evaluate_resume(self, ground_truth: Dict, predicted: Dict) -> Dict:
        """
        Evaluate the entire resume across all sections.
        
        Returns a dictionary with metrics for each section:
        - basics: Direct field comparison
        - work, education, skills, etc.: Entity alignment + field matching
        """
        results = {}
        
        # 1. Basics (single object)
        results["basics"] = self.evaluate_basics(
            ground_truth.get("basics"), 
            predicted.get("basics")
        )
        
        # 2. List-based sections with their specific configurations
        sections_config = {
            "work": {
                "key_fields": ["name", "position"],
                "fields": {
                    "name": "substring",
                    "position": "substring",
                    "startDate": "date",
                    "endDate": "date",
                    "summary": "text_similarity"
                }
            },
            "education": {
                "key_fields": ["institution", "area"],
                "fields": {
                    "institution": "substring",
                    "area": "substring",
                    "studyType": "substring",
                    "startDate": "date",
                    "endDate": "date"
                }
            },
            "skills": {
                "key_fields": ["name"],
                "fields": {
                    "name": "substring",
                    "level": "substring"
                }
            },
            "projects": {
                "key_fields": ["name"],
                "fields": {
                    "name": "substring",
                    "description": "text_similarity",
                    "startDate": "date",
                    "endDate": "date"
                }
            },
            "awards": {
                "key_fields": ["title"],
                "fields": {
                    "title": "substring",
                    "date": "date",
                    "awarder": "substring",
                    "summary": "text_similarity"
                }
            },
            "certificates": {
                "key_fields": ["name"],
                "fields": {
                    "name": "substring",
                    "date": "date",
                    "issuer": "substring"
                }
            },
            "publications": {
                "key_fields": ["name"],
                "fields": {
                    "name": "substring",
                    "publisher": "substring",
                    "releaseDate": "date",
                    "summary": "text_similarity"
                }
            },
            "languages": {
                "key_fields": ["language"],
                "fields": {
                    "language": "substring",
                    "fluency": "substring"
                }
            },
            "interests": {
                "key_fields": ["name"],
                "fields": {
                    "name": "substring"
                }
            },
            "volunteer": {
                "key_fields": ["organization", "position"],
                "fields": {
                    "organization": "substring",
                    "position": "substring",
                    "startDate": "date",
                    "endDate": "date",
                    "summary": "text_similarity"
                }
            },
            "references": {
                "key_fields": ["name"],
                "fields": {
                    "name": "substring",
                    "reference": "text_similarity"
                }
            }
        }
        
        # Evaluate each section
        for section, config in sections_config.items():
            gt_list = ground_truth.get(section, [])
            pred_list = predicted.get(section, [])
            results[section] = self.evaluate_section(gt_list, pred_list, config)
            
        return results
    
    def compute_overall_metrics(self, section_results: Dict) -> Dict:
        """
        Aggregate all section-level metrics into overall resume-level metrics.
        
        This computes weighted averages across all sections to provide a single
        quantitative measure of extraction quality, as described in the paper:
        "Finally, we aggregate the field-level matching outcomes across all
        evaluated resumes to compute quantitative performance metrics."
        
        IMPORTANT: Sections where both GT and Pred are empty are excluded from
        the overall calculation, as they represent perfect matches (no data to extract).
        
        Returns:
            Dict with overall precision, recall, F1, and average field accuracy
        """
        total_precision = 0.0
        total_recall = 0.0
        total_f1 = 0.0
        total_field_score = 0.0
        
        section_count = 0
        field_count = 0
        sections_with_data = []
        
        for section, metrics in section_results.items():
            # Skip sections where both GT and Pred are empty (F1=0, P=0, R=0)
            # These are "perfect" empty matches and shouldn't penalize the score
            if metrics["precision"] == 0.0 and metrics["recall"] == 0.0 and metrics["f1"] == 0.0:
                # Check if all field scores are also 0 (indicates empty section)
                field_scores = metrics.get("field_scores", {})
                if all(score == 0.0 for score in field_scores.values()):
                    continue  # Skip this section entirely
            
            # This section has actual data to evaluate
            sections_with_data.append(section)
            total_precision += metrics["precision"]
            total_recall += metrics["recall"]
            total_f1 += metrics["f1"]
            section_count += 1
            
            # Aggregate field scores (only non-zero fields)
            if metrics.get("field_scores"):
                for field, score in metrics["field_scores"].items():
                    # Only count fields that were actually evaluated (non-empty)
                    # A field with score 0.0 could mean mismatch OR both empty
                    # We include it in the count to reflect actual mismatches
                    total_field_score += score
                    field_count += 1
        
        overall = {
            "precision": total_precision / section_count if section_count > 0 else 1.0,
            "recall": total_recall / section_count if section_count > 0 else 1.0,
            "f1": total_f1 / section_count if section_count > 0 else 1.0,
            "avg_field_accuracy": total_field_score / field_count if field_count > 0 else 1.0,
            "sections_evaluated": section_count,
            "sections_with_data": sections_with_data,
            "fields_evaluated": field_count
        }
        
        return overall
