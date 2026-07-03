import re
from typing import List, Dict, Any
import uuid

class NumericExtractor:
    """
    Extracts numeric constraints (e.g. '10 minutes', '3 attempts') from raw text
    and returns them as specialized chunks to sidestep dense retrieval numeric blindness.
    """
    def __init__(self):
        # Regex to capture a number (digits, optionally with decimals/commas)
        # followed closely by common configuration units.
        # Captures: e.g., "10 minutes", "5 sec", "3 attempts", "8 characters"
        self.pattern = re.compile(
            r'\b(\d+(?:[,.]\d+)?)\s*(minutes?|mins?|seconds?|sec|hours?|days?|attempts?|characters?|chars?|bits?|bytes?|mb|gb|tb)\b',
            re.IGNORECASE
        )
        self.context_window = 100  # characters before and after to include

    def extract(self, text: str, doc_id: str) -> List[Dict[str, Any]]:
        """
        Scan text for numeric constraints and wrap them with surrounding context.
        """
        chunks = []
        for match in self.pattern.finditer(text):
            start = max(0, match.start() - self.context_window)
            end = min(len(text), match.end() + self.context_window)
            
            # Expand to nearest word boundaries if possible
            while start > 0 and not text[start].isspace():
                start -= 1
            while end < len(text) and not text[end-1].isspace():
                end += 1
                
            snippet = text[start:end].strip()
            # Clean up whitespace
            snippet = re.sub(r'\s+', ' ', snippet)
            
            val = match.group(1)
            unit = match.group(2)
            
            chunks.append({
                "id": str(uuid.uuid4()),
                "score": 1.0,
                "payload": {
                    "document_id": doc_id,
                    "text": snippet,
                    "metadata": {
                        "source": "numeric_extractor",
                        "value": val,
                        "unit": unit.lower(),
                        "match": match.group(0)
                    }
                }
            })
            
        # Deduplicate chunks that are functionally identical due to overlapping windows
        unique_chunks = []
        seen = set()
        for chunk in chunks:
            chunk_text = chunk.get("payload", {}).get("text", "")
            if chunk_text not in seen:
                seen.add(chunk_text)
                unique_chunks.append(chunk)
                
        return unique_chunks

    def is_numeric_requirement(self, text: str) -> bool:
        """
        Quick check if a requirement text involves numeric constraints.
        """
        return bool(self.pattern.search(text))
