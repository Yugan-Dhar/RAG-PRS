from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a document and return a list of parsed elements.
        Each element is typically a dict containing 'text' and 'metadata'.
        """
        pass
