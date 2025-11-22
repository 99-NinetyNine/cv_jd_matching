from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseMatcher(ABC):
    """Abstract base class for job matchers."""
    
    @abstractmethod
    def match(self, cv_data: Dict[str, Any], job_descriptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match a CV against a list of job descriptions.
        
        Args:
            cv_data: Structured data extracted from a CV
            job_descriptions: List of job descriptions to match against
            
        Returns:
            List of matches with scores and explanations
        """
        pass
