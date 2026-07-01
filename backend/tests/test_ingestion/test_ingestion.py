import pytest
from app.ingestion.parsers.plain_parser import PlainParser
from app.ingestion.chunker import HierarchicalChunker
from app.ingestion.embedder import BGEEmbedder
import os

def test_plain_parser(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Line 1\nLine 2\n\nLine 3")
    
    parser = PlainParser()
    elements = parser.parse(str(test_file))
    
    assert len(elements) == 3
    assert elements[0]["text"] == "Line 1"
    assert elements[2]["text"] == "Line 3"
    assert elements[0]["metadata"]["line_num"] == 1

def test_hierarchical_chunker():
    chunker = HierarchicalChunker(chunk_size=5, chunk_overlap=2)
    elements = [
        {"text": "one two three", "metadata": {"page": 1}},
        {"text": "four five six", "metadata": {"page": 1}},
        {"text": "seven eight", "metadata": {"page": 2}}
    ]
    
    chunks = chunker.chunk(elements)
    assert len(chunks) > 1
    # Chunk 1 should have up to 5 words
    assert "one two three four five" in chunks[0]["text"]

def test_embedder_mock():
    # If sentence-transformers is not installed, it returns a 384-dim dummy vector
    embedder = BGEEmbedder()
    emb = embedder.embed_query("test query")
    assert len(emb) == 384
