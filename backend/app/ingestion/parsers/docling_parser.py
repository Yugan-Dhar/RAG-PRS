import os
import logging
from typing import List, Dict, Any
from .base import BaseParser

logger = logging.getLogger(__name__)

class DoclingParser(BaseParser):
    def __init__(self):
        try:
            from docling.document_converter import DocumentConverter
            self.converter = DocumentConverter()
        except ImportError:
            logger.warning("docling not installed. DoclingParser will fail.")
            self.converter = None

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        if not self.converter:
            raise RuntimeError("docling is not installed")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Docling converting {file_path}")
        conv_result = self.converter.convert(file_path)
        doc = conv_result.document
        
        elements = []
        # Iterate over text elements. Docling v2 exposes `.texts` or we can export to markdown
        # Let's use export_to_markdown and chunk it later, or iterate items.
        # v2.107 Document has .texts, .tables, .pictures, etc.
        # Alternatively, we can just use the markdown export for unified chunking.
        
        md_text = doc.export_to_markdown()
        
        # For our parsed format, we'll store the markdown as a single element for the chunker to split
        # or we split it by basic paragraphs here.
        # Given that Docling handles layout, returning paragraphs is better.
        
        for p in md_text.split("\n\n"):
            p = p.strip()
            if p:
                elements.append({
                    "text": p,
                    "metadata": {
                        "type": "markdown",
                        "parser": "docling"
                    }
                })
                
        return elements
