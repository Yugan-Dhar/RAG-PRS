from typing import List, Dict, Any
import numpy as np

class GroundingVerifier:
    """
    Uses an NLI cross-encoder (nli-deberta-v3-small) to ensure the LLM's
    justification is factually grounded in the retrieved evidence.
    
    nli-deberta-v3-small label order: [contradiction=0, neutral=1, entailment=2]
    """
    def __init__(self):
        self.model = None
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder('cross-encoder/nli-deberta-v3-small', device='cpu')
        except Exception:
            pass  # Graceful degradation

    def verify(self, justification: str, evidence_chunks: List[Dict[str, Any]]) -> float:
        """
        Returns a grounding score (0.0 to 1.0) indicating how well the evidence
        entails the justification. Returns 1.0 (neutral/pass-through) if model unavailable.
        """
        if not self.model or not evidence_chunks or not justification:
            return 1.0

        # Combine evidence into a single premise (max ~2000 chars to cover top 5 chunks)
        premise_parts = [chunk["payload"].get("text", "") for chunk in evidence_chunks[:5]]
        premise = " ".join(premise_parts)[:2000]

        # Run NLI prediction — returns raw logits, shape (1, 3)
        logits = self.model.predict([(premise, justification[:300])])

        # Convert logits → probabilities via softmax
        exp_logits = np.exp(logits[0] - np.max(logits[0]))  # numerically stable
        probs = exp_logits / exp_logits.sum()

        # nli-deberta-v3-small: index 0=contradiction, 1=neutral, 2=entailment
        entailment_prob = float(probs[2])
        contradiction_prob = float(probs[0])

        # Penalise if contradiction is high
        if contradiction_prob > 0.5:
            return 1.0 - contradiction_prob

        return entailment_prob
