from typing import List, Dict, Any

class NegationDetector:
    """
    Detects if the capability is mentioned but explicitly negated
    (e.g., 'does not support SSH').
    For MVP, uses simple keyword matching. SpaCy dependency parser can improve this.
    """
    def __init__(self):
        self.negation_tokens = {"not", "no", "unsupported", "cannot", "doesn't", "don't", "lacks", "without"}

    def detect(self, text: str, concept: str) -> bool:
        """
        Returns True if the concept is likely negated in the text.
        """
        text_lower = text.lower()
        concept_lower = concept.lower()
        
        # Find where concept is mentioned
        idx = text_lower.find(concept_lower)
        if idx == -1:
            return False
            
        # Look at the words immediately preceding the concept (window of 5 words)
        preceding_text = text_lower[max(0, idx - 30):idx]
        tokens = preceding_text.split()
        
        for token in tokens[-5:]:
            if token in self.negation_tokens:
                return True
                
        return False
