from typing import List, Dict, Any

class EvidenceQualityAssessor:
    """
    Assesses the quality of the evidence (e.g. recency, authority, document type).
    For PRS MVP, we look at metadata: is it from a standard, manual, or test report?
    """
    def __init__(self):
        # Weights for document types
        self.type_weights = {
            "standard": 1.0,
            "security_target": 1.0,
            "configuration_guide": 0.9,
            "datasheet": 0.6,
            "unknown": 0.5
        }

    def _infer_doc_type(self, meta: dict) -> str:
        """Infer document type from metadata when doc_type is not explicitly set."""
        doc_type = meta.get("doc_type", "").lower()
        if doc_type and doc_type != "unknown":
            return doc_type
        filename = meta.get("filename", meta.get("doc_id", "")).lower()
        if any(kw in filename for kw in ["security_target", "st_", "cc_", "evaluation"]):
            return "security_target"
        if any(kw in filename for kw in ["guide", "manual", "config", "admin"]):
            return "configuration_guide"
        if any(kw in filename for kw in ["datasheet", "product", "spec"]):
            return "datasheet"
        return "unknown"

    def assess(self, evidence_chunks: List[Dict[str, Any]]) -> float:
        if not evidence_chunks:
            return 0.0
            
        total_weight = 0.0
        for chunk in evidence_chunks[:3]:
            meta = chunk.get("payload", {}).get("metadata", {})
            doc_type = self._infer_doc_type(meta)
            total_weight += self.type_weights.get(doc_type, 0.5)
            
        return total_weight / min(3, len(evidence_chunks))
