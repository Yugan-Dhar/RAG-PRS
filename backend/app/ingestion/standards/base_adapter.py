from abc import ABC, abstractmethod
from typing import List, Dict, Any

class StandardAdapter(ABC):
    @abstractmethod
    def load_framework(self, standard_id: str, framework_id: str) -> List[Dict[str, Any]]:
        """
        Load the requirements for a specific standard and framework.
        Returns a list of requirement dictionaries.
        """
        pass
        
    @abstractmethod
    def parse_document(self, document_path: str, framework_id: str) -> List[Dict[str, Any]]:
        """
        Extract requirements directly from an uploaded PDF standard document.
        """
        pass
