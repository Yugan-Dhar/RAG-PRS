import sys
import os
import json
import logging
from typing import List, Dict, Any

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from app.ingestion.chunker import HierarchicalChunker
from app.ingestion.embedder import BGEEmbedder
from app.ingestion.indexer import QdrantIndexer, BM25Indexer
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.query_expander import QueryExpander
from app.retrieval.reranker import Reranker
from app.ingestion.standards.itsar_adapter import ITSARAdapter

# Suppress overly verbose logs
logging.basicConfig(level=logging.WARNING)

def build_retrieval_query(requirement: Dict[str, Any]) -> str:
    keywords = requirement.get("keywords", [])
    title = requirement.get("title", "")
    if keywords:
        parts = ([title] if title else []) + keywords[:5]
        return " ".join(parts)
    return title

def main():
    if len(sys.argv) < 2:
        print("Usage: python evaluate_retriever.py <path_to_pdf_or_txt>")
        sys.exit(1)

    file_path = sys.argv[1]
    
    if file_path.lower().endswith(".pdf"):
        import pymupdf
        pdf_doc = pymupdf.open(file_path)
        text = "\n".join([page.get_text() for page in pdf_doc])
    else:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='utf-16') as f:
                text = f.read()

    print("Chunking document...")
    chunker = HierarchicalChunker(chunk_size=400, chunk_overlap=80)
    doc_id = "eval_doc"
    chunks = chunker.chunk_text(text, doc_id)
    
    print("Embedding document...")
    embedder = BGEEmbedder()
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.embed_documents(texts)
    
    print("Indexing document...")
    dense_idx = QdrantIndexer()
    sparse_idx = BM25Indexer()
    dense_idx.index(chunks, embeddings)
    sparse_idx.index(chunks)
    
    retriever = HybridRetriever(dense_idx, sparse_idx)
    expander = QueryExpander()
    reranker = Reranker()
    
    print("Loading requirements (ITSAR-ROUTER)...")
    adapter = ITSARAdapter()
    reqs = adapter.load_framework("ITSAR", "ITSAR-ROUTER")
    
    # Flatten requirements for easy iteration
    flat_reqs = []
    for section in reqs:
        for child in section.get("children", []):
            flat_reqs.append(child)
            
    print(f"Starting evaluation of {len(flat_reqs)} requirements...")
    
    report = ["# Retriever Validation Report", f"**Document:** {file_path}", f"**Total Requirements Evaluated:** {len(flat_reqs)}", ""]
    
    zero_chunks_count = 0
    zero_rerank_count = 0
    
    for req in flat_reqs:
        req_id = req.get("id", "Unknown")
        title = req.get("title", "No Title")
        query = build_retrieval_query(req)
        
        report.append(f"## {req_id}: {title}")
        report.append(f"**Query:** `{query}`")
        
        expanded = expander.expand(query)
        report.append(f"**Expanded Query terms:** `{', '.join(expanded)}`")
        
        # 1. Retrieve (Hybrid)
        candidate_chunks = retriever.retrieve(query, top_k=20)
        
        if not candidate_chunks:
            zero_chunks_count += 1
            report.append("**Result:** ❌ 0 chunks retrieved by Dense/BM25")
            report.append("---")
            continue
            
        report.append(f"**Hybrid Retrieval:** {len(candidate_chunks)} candidate chunks found")
        
        # 2. Rerank
        shared_evidence = reranker.rerank(query, candidate_chunks, top_k=5)
        
        if not shared_evidence:
            zero_rerank_count += 1
            report.append("**Result:** ❌ 0 chunks survived the Reranker")
            report.append("---")
            continue
            
        report.append(f"**Reranker Output:** {len(shared_evidence)} chunks survived")
        report.append("\n### Top 3 Evidence Chunks:\n")
        
        for i, chunk in enumerate(shared_evidence[:3]):
            chunk_id = chunk.get("id", "unknown")
            cosine = chunk.get("cosine_score", 0.0)
            rrf = chunk.get("score", 0.0)
            rerank = chunk.get("rerank_score", 0.0)
            
            snippet = chunk.get("payload", {}).get("text", "")
            snippet = snippet[:400].replace('\n', ' ') + "..."
            
            report.append(f"**Chunk ID:** {chunk_id} | **Cosine:** {cosine:.4f} | **RRF:** {rrf:.4f} | **Rerank Logit:** {rerank:.4f}")
            report.append(f"> {snippet}\n")
            
        report.append("---\n")
        
    report.insert(4, f"**Summary:**")
    report.insert(5, f"- Requirements with 0 initial chunks: {zero_chunks_count}")
    report.insert(6, f"- Requirements with 0 reranked chunks: {zero_rerank_count}")
    report.insert(7, "")
        
    report_path = "retrieval_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"\nEvaluation complete! Report saved to {report_path}")

if __name__ == "__main__":
    main()
