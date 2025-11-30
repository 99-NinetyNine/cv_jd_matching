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
