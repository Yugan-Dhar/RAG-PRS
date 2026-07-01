from typing import List, Dict, Any
from app.ingestion.standards.itsar_router_config import ITSARRouterConfig


class ApplicabilityEngine:
    @staticmethod
    def _is_applicable(req: Dict[str, Any], config: ITSARRouterConfig) -> bool:
        allowed_types = req.get("applicable_router_types", [])
        if allowed_types and config.router_type not in allowed_types:
            return False

        required_flags = req.get("required_capability_flags", [])
        if required_flags:
            missing_flags = [flag for flag in required_flags if flag not in config.capability_flags]
            if missing_flags:
                return False

        return True

    @classmethod
    def filter_requirements(cls, requirements: List[Dict[str, Any]], config: ITSARRouterConfig) -> List[Dict[str, Any]]:
        applicable_groups = []
        for req in requirements:
            children = req.get("children")
            if children is None:
                if cls._is_applicable(req, config):
                    applicable_groups.append(req)
                continue

            filtered_children = [child for child in children if cls._is_applicable(child, config)]
            if not filtered_children:
                continue

            req_copy = dict(req)
            req_copy["children"] = filtered_children
            applicable_groups.append(req_copy)

        return applicable_groups
