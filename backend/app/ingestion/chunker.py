import uuid
import re
from typing import List, Dict, Any

class HierarchicalChunker:
    """
    Splits a document into overlapping word-based chunks suitable for embedding.
    Fixed to correctly split large texts rather than treating the entire document as one element.
    """
    def __init__(self, chunk_size: int = 300, chunk_overlap: int = 50):
        self.chunk_size = chunk_size      # words per chunk
        self.chunk_overlap = chunk_overlap  # words of overlap between chunks

    def chunk_text(self, text: str, doc_id: str) -> List[Dict[str, Any]]:
        """
        Split `text` into overlapping word-window chunks and return structured chunk dicts.
        """
        # ── 1. Clean the text ────────────────────────────────────────────────
        # Collapse excessive blank lines and whitespace runs
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.strip()

        if not text:
            return []

        # ── 2. Tokenise into words (keep newlines as word boundaries) ────────
        words = text.split()
        total_words = len(words)

        if total_words == 0:
            return []

        # ── 3. Slide a window across the word list ───────────────────────────
        chunks = []
        chunk_idx = 0
        start = 0

        while start < total_words:
            end = min(start + self.chunk_size, total_words)
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            chunks.append({
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "chunk_index": chunk_idx,
                "text": chunk_text,
                "metadata": {"doc_id": doc_id, "chunk_index": chunk_idx,
                             "start_word": start, "end_word": end}
            })
            chunk_idx += 1

            # Advance by (chunk_size - overlap) so consecutive chunks share context
            stride = self.chunk_size - self.chunk_overlap
            if stride <= 0:
                stride = max(1, self.chunk_size // 2)
            start += stride

        return chunks

    # Keep the legacy `chunk()` method for any callers that pass pre-split elements
    def chunk(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Legacy element-based chunking — joins all elements then re-chunks."""
        combined = "\n".join(el.get("text", "") for el in elements)
        doc_id = elements[0].get("metadata", {}).get("doc_id", "unknown") if elements else "unknown"
        raw = self.chunk_text(combined, doc_id)
        # Return in the old format (without id/document_id) for backward compatibility
        return [{"chunk_index": c["chunk_index"], "text": c["text"],
                 "metadata": c["metadata"]} for c in raw]
