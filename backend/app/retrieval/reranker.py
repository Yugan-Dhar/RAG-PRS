from typing import List, Dict, Any, Optional
import numpy as np

class Reranker:
    """
    Reranks candidate chunks using BGE Embeddings to ensure high semantic relevance.
    Filters out chunks below a strict cosine similarity threshold.
    """
    def __init__(self):
        from app.ingestion.embedder import BGEEmbedder
        self.embedder = BGEEmbedder()

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5, min_score: float = 0.20) -> List[Dict[str, Any]]:
        """
        Rerank chunks by computing dense cosine similarity with the query.
        """
        if not chunks:
            return []

        # If they already have cosine_score from dense retrieval, use that?
        # Better: Re-embed the chunks if they don't have it, or just use what they have.
        # But wait, we want to score BM25-only chunks too!
        
        # Collect texts to embed for chunks that are missing a valid cosine_score
        texts_to_embed = []
        indices_to_embed = []
        
        for i, chunk in enumerate(chunks):
            # If the chunk came purely from BM25, its cosine_score might be 0.0 or missing.
            if chunk.get("cosine_score", 0.0) <= 0.0:
                texts_to_embed.append(chunk.get("payload", {}).get("text", ""))
                indices_to_embed.append(i)
                
        if texts_to_embed:
            q_emb = np.array(self.embedder.embed_query(query))
            c_embs = np.array(self.embedder.embed_documents(texts_to_embed))
            sims = np.dot(c_embs, q_emb)
            
            for sim, idx in zip(sims, indices_to_embed):
                chunks[idx]["cosine_score"] = float(sim)
                chunks[idx]["rerank_score"] = float(sim)  # backwards compatibility
                
        for chunk in chunks:
            if "rerank_score" not in chunk:
                chunk["rerank_score"] = float(chunk.get("cosine_score", 0.0))

        # Filter out chunks with low cosine similarity
        filtered_chunks = [c for c in chunks if c.get("cosine_score", 0.0) >= min_score]

        # Sort by cosine score descending
        reranked = sorted(filtered_chunks, key=lambda c: c.get("cosine_score", 0.0), reverse=True)
        return reranked[:top_k]
