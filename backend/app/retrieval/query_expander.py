from typing import List, Dict, Tuple
from app.knowledge.ontology import get_ontology
from app.schemas.capability import CapabilityObject

class QueryExpander:
    """
    Uses the Security Ontology to expand queries for higher recall.
    """
    def __init__(self):
        self.ontology = get_ontology()

    def expand(self, query: str) -> List[str]:
        """Returns the original query plus expanded related concepts."""
        expanded_terms = self.ontology.get_related_terms(query)
        # Fallback if no matching concept found
        if not expanded_terms:
            return [query]
            
        return list(dict.fromkeys(expanded_terms))  # Preserve order, remove duplicates
        
    def extract_capabilities(self, query: str) -> List[CapabilityObject]:
        """
        Parses a requirement query into expected CapabilityObjects.
        (Delegates to CapabilityExtractor, but exposed here for convenience if needed)
        """
        # In a real setup, we'd inject the CapabilityExtractor here
        from app.knowledge.capability_extractor import CapabilityExtractor
        extractor = CapabilityExtractor()
        return extractor.extract(query)
