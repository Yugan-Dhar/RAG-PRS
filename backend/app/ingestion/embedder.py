import numpy as np
from typing import List, Union

class BGEEmbedder:
    """
    CPU-based BGE-small embedder using sentence-transformers.
    Model: BAAI/bge-small-en-v1.5
    """
    def __init__(self):
        try:
            import os
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            from sentence_transformers import SentenceTransformer
            # Uses CPU by default if PyTorch is not compiled with CUDA
            self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu", local_files_only=True)
        except ImportError:
            self.model = None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed document chunks (no query prefix required for BGE for docs)."""
        if not self.model:
            return [[0.0] * 384 for _ in texts] # Dummy 384-dim
        
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """BGE requires prefix for queries: 'Represent this sentence for searching relevant passages: '"""
        if not self.model:
            return [0.0] * 384
            
        prefixed_query = f"Represent this sentence for searching relevant passages: {query}"
        embedding = self.model.encode(prefixed_query, normalize_embeddings=True)
        return embedding.tolist()
