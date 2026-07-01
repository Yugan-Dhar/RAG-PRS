from typing import List, Dict, Any
from app.ingestion.embedder import BGEEmbedder
from app.ingestion.indexer import QdrantIndexer, BM25Indexer
from .query_expander import QueryExpander

class HybridRetriever:
    """
    Combines Dense Retrieval (BGE/Qdrant) and Sparse Retrieval (BM25)
    using Reciprocal Rank Fusion (RRF).
    """
    def __init__(self, dense_indexer: QdrantIndexer, sparse_indexer: BM25Indexer):
        self.dense = dense_indexer
        self.sparse = sparse_indexer
        self.embedder = BGEEmbedder()
        self.expander = QueryExpander()

    def rrf_fusion(self, dense_results: List[Dict], sparse_results: List[Dict], k: int = 60) -> List[Dict]:
        """Reciprocal Rank Fusion — also carries the best raw cosine score per chunk."""
        rrf_scores = {}
        cosine_scores = {}  # track best raw cosine similarity per doc
        payloads = {}
        
        for rank, res in enumerate(dense_results):
            doc_id = res["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            payloads[doc_id] = res["payload"]
            # Preserve the best raw cosine score from Qdrant
            raw = res.get("cosine_score", res.get("score", 0.0))
            if raw > cosine_scores.get(doc_id, 0.0):
                cosine_scores[doc_id] = raw
            
        for rank, res in enumerate(sparse_results):
            doc_id = res["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            payloads[doc_id] = res["payload"]
            # BM25 scores can be very high; don't use them for cosine_score
            if doc_id not in cosine_scores:
                cosine_scores[doc_id] = 0.0
            
        fused = [
            {
                "id": doc_id,
                "score": rrf_scores[doc_id],          # RRF score (for ranking)
                "cosine_score": cosine_scores.get(doc_id, 0.0),  # Real similarity (for Tier1)
                "payload": payloads[doc_id]
            }
            for doc_id in sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])
        ]
        
        return fused

    def retrieve(self, dense_query: str, sparse_query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        # 1. Dense retrieval (Semantic search using natural language)
        query_embedding = self.embedder.embed_query(dense_query)
        dense_results = self.dense.search(query_embedding, top_k=top_k*2)
        
        # 2. Sparse retrieval (Keyword search using expanded terms)
        sparse_results = self.sparse.search(sparse_query, top_k=top_k*2)
        
        # 3. Fusion
        fused_results = self.rrf_fusion(dense_results, sparse_results)
        
        return fused_results[:top_k]
