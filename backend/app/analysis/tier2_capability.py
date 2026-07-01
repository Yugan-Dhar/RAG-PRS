from typing import List, Dict, Any, Tuple
from app.schemas.capability import CapabilityObject
from app.knowledge.ontology import get_ontology
from app.knowledge.capability_extractor import CapabilityExtractor

class Tier2Capability:
    """
    Tier 2 Capability Analysis: Compares Expected Capabilities from the Requirement
    against Observed Capabilities extracted from the Evidence chunks.
    """
    def __init__(self):
        self.ontology = get_ontology()
        self.extractor = CapabilityExtractor()

    def analyze(self, expected: List[CapabilityObject], evidence_chunks: List[Dict[str, Any]]) -> Tuple[float, List[CapabilityObject], List[CapabilityObject]]:
        """
        Returns: (capability_score, observed, missing)
        """
        if not expected:
            # No structured capabilities could be parsed — treat as N/A (no penalisation)
            return 1.0, [], []

        # Combine text from top evidence chunks
        combined_text = " ".join([chunk["payload"].get("text", "") for chunk in evidence_chunks[:3]])
        
        # Extract observed capabilities
        observed = self.extractor.extract(combined_text)
        
        missing = []
        total_score = 0.0
        
        for exp in expected:
            best_match_score = 0.0
            for obs in observed:
                score = exp.matches(obs, self.ontology)
                if score > best_match_score:
                    best_match_score = score
            
            total_score += best_match_score
            if best_match_score < 0.5:
                missing.append(exp)
                
        final_score = total_score / len(expected)
        return final_score, observed, missing
