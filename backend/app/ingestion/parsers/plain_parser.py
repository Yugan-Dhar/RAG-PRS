from typing import List, Dict, Any
import os
from .base import BaseParser

class PlainParser(BaseParser):
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        elements = []
        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                elements.append({
                    "text": line,
                    "metadata": {
                        "type": "text",
                        "page_num": 1,
                        "line_num": i + 1
                    }
                })
        return elements
