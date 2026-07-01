import asyncio
import json
import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from app.ingestion.chunker import HierarchicalChunker
from app.ingestion.embedder import BGEEmbedder
from app.ingestion.indexer import QdrantIndexer, BM25Indexer
from app.retrieval.hybrid_retriever import HybridRetriever

# Read the test file
with open('../test_router_manual.txt', 'r') as f:
    text = f.read()

print(f"Test file length: {len(text)} chars")

chunker = HierarchicalChunker(chunk_size=300, chunk_overlap=50)
chunks = chunker.chunk_text(text, 'test_doc')
print(f"Chunks created: {len(chunks)}")
print("--- SAMPLE CHUNK ---")
print(chunks[0]['text'][:300])
print("---")

embedder = BGEEmbedder()
embeddings = embedder.embed_documents([c['text'] for c in chunks])
print(f"Embeddings: {len(embeddings)} vectors of dim {len(embeddings[0])}")

dense_idx = QdrantIndexer(location=':memory:')
sparse_idx = BM25Indexer()
dense_idx.index(chunks, embeddings)
sparse_idx.index(chunks)

retriever = HybridRetriever(dense_indexer=dense_idx, sparse_indexer=sparse_idx)

# Test queries
queries = [
    "IP Router shall support mutual authentication of entities on management interfaces",
    "Router shall not support FTP TFTP Telnet services",
    "password complexity minimum 8 characters uppercase lowercase digit special character"
]

for query in queries:
    results = retriever.retrieve(query, top_k=3)
    print(f"\nQUERY: {query[:80]}")
    for r in results:
        score = r.get('score', 0)
        text_snippet = r['payload'].get('text', '')[:150]
        print(f"  Score={score:.4f} | Text: {text_snippet}")
