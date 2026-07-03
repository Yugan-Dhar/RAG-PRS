import json
from typing import List, Dict, Any
from pathlib import Path
from .base_adapter import StandardAdapter


class ITSARAdapter(StandardAdapter):
    def __init__(self, data_dir: str | None = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent.parent / "knowledge" / "data"
        else:
            self.data_dir = Path(data_dir)

    def load_framework(self, standard_id: str, framework_id: str) -> List[Dict[str, Any]]:
        if standard_id != "ITSAR":
            raise ValueError(f"ITSARAdapter only supports ITSAR, got {standard_id}")

        mapping = {
            "ITSAR-ROUTER": "itsar_router_v2.json",
            "ITSAR-LAN": "itsar_lan_switch_v1.json",
        }

        filename = mapping.get(framework_id)
        if not filename:
            raise ValueError(f"Unknown ITSAR framework: {framework_id}")

        file_path = self.data_dir / filename
        if not file_path.exists():
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        groups = []
        for section in data.get("sections", []):
            section_id = section.get("id")
            section_title = section.get("title")
            section_chapter = section.get("chapter", "")

            section_keywords: List[str] = []
            children: List[Dict[str, Any]] = []

            for req in section.get("requirements", []):
                req_copy = dict(req)
                req_copy["chapter"] = section_chapter
                req_copy["section_number"] = section_id
                req_copy["section_title"] = section_title
                req_copy.setdefault("keywords", [])
                req_copy["mandatory_concepts"] = list(dict.fromkeys(req_copy.get("keywords", [])))
                children.append(req_copy)

                for kw in req_copy.get("keywords", []):
                    if kw not in section_keywords:
                        section_keywords.append(kw)

                for sub_req in req.get("sub_requirements", []):
                    sub_copy = dict(sub_req)
                    sub_copy["chapter"] = section_chapter
                    sub_copy["section_number"] = section_id
                    sub_copy["section_title"] = section_title
                    sub_copy["parent_req_id"] = req.get("id")
                    sub_copy.setdefault("applicable_router_types", req.get("applicable_router_types", []))
                    sub_copy.setdefault("required_capability_flags", req.get("required_capability_flags", []))
                    sub_copy.setdefault("is_prohibition", req.get("is_prohibition", False))
                    sub_copy.setdefault("compliance_by_undertaking", req.get("compliance_by_undertaking", False))
                    sub_copy.setdefault("keywords", req.get("keywords", []))
                    sub_copy["mandatory_concepts"] = list(dict.fromkeys(sub_copy.get("keywords", [])))
                    children.append(sub_copy)

            req_titles = [r.get("title", r.get("id", "")) for r in section.get("requirements", [])]
            group_text = f"{section_title}: " + "; ".join(req_titles)
            groups.append(
                {
                    "id": section_id,
                    "title": section_title,
                    "text": group_text,
                    "keywords": section_keywords,
                    "mandatory_concepts": section_keywords,
                    "chapter": section_chapter,
                    "section_number": section_id,
                    "section_title": section_title,
                    "node_type": "SECTION_GROUP",
                    "applicable_router_types": [],
                    "required_capability_flags": [],
                    "is_prohibition": False,
                    "compliance_by_undertaking": False,
                    "children": children,
                }
            )

        return groups

    def parse_document(self, document_path: str, framework_id: str) -> List[Dict[str, Any]]:
        return []
