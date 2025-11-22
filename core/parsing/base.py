from abc import ABC, abstractmethod
from typing import Dict, Any, Union
from pathlib import Path

class BaseParser(ABC):
    """Abstract base class for document parsers."""
    
    @abstractmethod
    def parse(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse a file and return structured data.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Dict containing extracted information
        """
        pass
