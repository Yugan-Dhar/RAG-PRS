import json
import os
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class QdrantIndexer:
    """
    Qdrant vector store wrapper. Supports local in-memory or disk-backed mode.
    """

    def __init__(self, collection_name: str = "prs_chunks", location: str = ":memory:"):
        self.collection_name = collection_name
        self.location = location
        if location != ":memory:":
            os.makedirs(location, exist_ok=True)
        if location == ":memory:":
            self.client = QdrantClient(location=location)
        else:
            self.client = QdrantClient(path=location)

        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

    def index(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        points = []
        for chunk, emb in zip(chunks, embeddings):
            chunk_id = chunk.get("id", str(uuid.uuid4()))
            chunk["id"] = chunk_id
            points.append(
                PointStruct(
                    id=chunk_id,
                    vector=emb,
                    payload=chunk,
                )
            )

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
        ).points
        return [
            {"id": hit.id, "score": hit.score, "cosine_score": hit.score, "payload": hit.payload}
            for hit in results
        ]


class BM25Indexer:
    """
    BM25 indexer with optional on-disk persistence for shared retrieval reuse.
    """

    def __init__(self, persist_path: str | None = None):
        try:
            from rank_bm25 import BM25Okapi
            self.BM25Okapi = BM25Okapi
        except ImportError:
            self.BM25Okapi = None

        self.persist_path = persist_path
        self.chunks: List[Dict[str, Any]] = []
        self.chunk_ids: set[str] = set()
        self.bm25 = None
        self.corpus_tokens: List[List[str]] = []
        self._load_if_present()

    def _tokenize(self, text: str) -> List[str]:
        return text.lower().split()

    def _rebuild_index(self):
        if not self.BM25Okapi or not self.chunks:
            self.bm25 = None
            self.corpus_tokens = []
            return
        self.corpus_tokens = [self._tokenize(chunk.get("text", "")) for chunk in self.chunks]
        self.bm25 = self.BM25Okapi(self.corpus_tokens)

    def _load_if_present(self):
        if not self.persist_path or not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
            self.chunk_ids = {str(chunk.get("id")) for chunk in self.chunks if chunk.get("id")}
            self._rebuild_index()
        except Exception:
            self.chunks = []
            self.chunk_ids = set()
            self.bm25 = None
            self.corpus_tokens = []

    def _persist(self):
        if not self.persist_path:
            return
        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
        temp_path = f"{self.persist_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=True)
        os.replace(temp_path, self.persist_path)

    def index(self, chunks: List[Dict[str, Any]]):
        if not self.BM25Okapi:
            return

        new_chunks = []
        for chunk in chunks:
            chunk_id = chunk.get("id") or str(uuid.uuid4())
            chunk["id"] = chunk_id
            if chunk_id in self.chunk_ids:
                continue
            self.chunk_ids.add(chunk_id)
            new_chunks.append(chunk)

        if not new_chunks:
            return

        self.chunks.extend(new_chunks)
        self._rebuild_index()
        self._persist()

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        if not self.bm25:
            return []

        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            {"id": self.chunks[i].get("id"), "score": scores[i], "payload": self.chunks[i]}
            for i in top_indices
        ]
