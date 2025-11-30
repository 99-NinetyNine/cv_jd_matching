from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate_section(self, ground_truth: List[Dict], predicted: List[Dict], config: Dict) -> Dict:
        """
        Evaluate a section of the resume.
        """
        pass
