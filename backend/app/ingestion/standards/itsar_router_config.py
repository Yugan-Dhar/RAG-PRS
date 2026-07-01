from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ITSARRouterConfig:
    router_type: str  # "conventional", "sdn", "cloud_native", "virtual", "cloud_managed"
    capability_flags: List[str]  # e.g. ["web_interface", "api_support", "wifi", "napt", "layer2"]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            router_type=data.get("router_type", "conventional"),
            capability_flags=data.get("capability_flags", [])
        )
