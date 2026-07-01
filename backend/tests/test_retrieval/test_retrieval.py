import json
import pytest
from app.retrieval.query_expander import QueryExpander
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.reranker import Reranker
from app.ingestion.indexer import BM25Indexer


def test_query_expander():
    expander = QueryExpander()
    expanded = expander.expand("ssh")
    assert "ssh" in expanded
    assert len(expanded) >= 1


def test_reranker_mock():
    reranker = Reranker()
    docs = [
        {"id": "1", "payload": {"text": "apple"}},
        {"id": "2", "payload": {"text": "banana"}},
        {"id": "3", "payload": {"text": "orange"}},
    ]
    ranked = reranker.rerank("fruit", docs, top_k=2)
    assert len(ranked) == 2


def test_hybrid_retriever_fusion():
    class MockDense:
        def search(self, query_emb, top_k):
            return [
                {"id": "A", "score": 0.9, "cosine_score": 0.9, "payload": {}},
                {"id": "B", "score": 0.8, "cosine_score": 0.8, "payload": {}},
            ]

    class MockSparse:
        def search(self, query, top_k):
            return [
                {"id": "B", "score": 10.0, "payload": {}},
                {"id": "C", "score": 5.0, "payload": {}},
            ]

    retriever = HybridRetriever(dense_indexer=MockDense(), sparse_indexer=MockSparse())

    class MockEmbedder:
        def embed_query(self, query):
            return [0.1]

    class MockExpander:
        def expand(self, query):
            return [query]

    retriever.embedder = MockEmbedder()
    retriever.expander = MockExpander()

    results = retriever.retrieve("test", top_k=3)
    assert results[0]["id"] == "B"
    assert len(results) == 3


def test_bm25_persistence(tmp_path):
    store = tmp_path / "bm25_chunks.json"
    chunks = [
        {"id": "c1", "text": "router supports ssh and role based access control"},
        {"id": "c2", "text": "ftp is not supported on this router"},
    ]
    indexer = BM25Indexer(persist_path=str(store))
    indexer.index(chunks)

    reloaded = BM25Indexer(persist_path=str(store))
    results = reloaded.search("ssh router", top_k=1)
    assert store.exists()
    assert len(results) == 1
    assert results[0]["id"] == "c1"
