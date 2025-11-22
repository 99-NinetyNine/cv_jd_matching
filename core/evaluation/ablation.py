from typing import Dict, List, Any
from core.evaluation.metrics import Evaluator
from core.matching.semantic_matcher import HybridMatcher
import logging

logger = logging.getLogger(__name__)

class AblationStudy:
    def __init__(self, ground_truth: Dict[str, List[str]], cvs: List[Dict], jobs: List[Dict]):
        self.ground_truth = ground_truth
        self.cvs = cvs
        self.jobs = jobs
        self.evaluator = Evaluator()
        
    def run_experiment(self, config_name: str, matcher_config: Dict[str, Any]) -> Dict[str, float]:
        logger.info(f"Running experiment: {config_name}")
        
        # Configure matcher based on experiment
        # Note: This requires HybridMatcher to be configurable. 
        # For now, we assume we can toggle features via flags or subclassing.
        # Let's assume HybridMatcher takes flags.
        
        # Mocking the config application for this demo
        matcher = HybridMatcher() # In real implementation, pass config
        
        predictions = {}
        for cv in self.cvs:
            # Mock ID
            cv_id = cv.get("id", "unknown") 
            matches = matcher.match(cv, self.jobs)
            predictions[cv_id] = [m["job_id"] for m in matches]
            
        return self.evaluator.evaluate(self.ground_truth, predictions)

    def run_all(self):
        experiments = {
            "baseline": {"use_semantic": False, "use_keyword": True, "rerank": False},
            "semantic_only": {"use_semantic": True, "use_keyword": False, "rerank": False},
            "hybrid": {"use_semantic": True, "use_keyword": True, "rerank": False},
            "full_pipeline": {"use_semantic": True, "use_keyword": True, "rerank": True}
        }
        
        results = {}
        for name, config in experiments.items():
            results[name] = self.run_experiment(name, config)
            
        return results
