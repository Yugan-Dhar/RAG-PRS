from typing import List, Dict, Any, Optional
from app.ingestion.embedder import BGEEmbedder

class Reranker:
    """
    Cross-encoder reranker using ms-marco-MiniLM-L-6-v2.
    Takes a list of candidate chunks from RRF fusion and re-scores them
    by computing a relevance score between the query and each chunk.
    This significantly improves precision over purely embedding-based retrieval.
    """
    def __init__(self):
        self.model = None
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device='cpu', max_length=512)
        except Exception:
            pass  # Graceful degradation: skip reranking if unavailable

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank chunks by (query, chunk_text) relevance.
        Returns top_k chunks with a 'rerank_score' field added.
        Falls back to original order if model unavailable.
        """
        if not self.model or not chunks:
            return chunks[:top_k]

        pairs = [(query, chunk["payload"].get("text", "")[:500]) for chunk in chunks]
        scores = self.model.predict(pairs)

        # Attach rerank score to each chunk
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        # Sort by rerank score descending
        reranked = sorted(chunks, key=lambda c: c.get("rerank_score", 0.0), reverse=True)
        return reranked[:top_k]
