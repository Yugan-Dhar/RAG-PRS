import asyncio
import time
import json
from app.retrieval.hybrid_retriever import HybridRetriever
from app.ingestion.indexer import QdrantIndexer, BM25Indexer
from app.retrieval.reranker import Reranker
from app.analysis.tier3_llm import Tier3LLM
from app.analysis.orchestrator import AssessmentOrchestrator

async def profile_analysis():
    print("Loading models...")
    start = time.time()
    dense = QdrantIndexer(collection_name="test_profile")
    sparse = BM25Indexer(persist_path="./bm25_profile")
    retriever = HybridRetriever(dense, sparse)
    reranker = Reranker()
    llm = Tier3LLM()
    print(f"Models loaded in {time.time() - start:.2f}s")
    
    query = "mutual authentication of entities on management interfaces"
    
    print("Profiling Retrieval...")
    start = time.time()
    chunks = retriever.retrieve(query, top_k=10)
    print(f"Retrieval took {time.time() - start:.2f}s")
    
    print("Profiling Reranker...")
    start = time.time()
    reranked = reranker.rerank(query, chunks, top_k=5)
    print(f"Reranker took {time.time() - start:.2f}s")
    
    print("Profiling LLM...")
    start = time.time()
    res = await llm.analyze_requirement(query, query, reranked)
    print(f"LLM took {time.time() - start:.2f}s")
    
if __name__ == "__main__":
    asyncio.run(profile_analysis())
