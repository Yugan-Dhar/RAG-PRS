import json
import networkx as nx
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache

@dataclass
class OntologyNode:
    id: str
    label: str
    aliases: list[str]
    domain: str

@dataclass
class ConceptExpansion:
    seed_concept: str
    expanded_concepts: list[tuple[str, float]]  # (concept_label, weight)
    traversal_path: list[str]

class SecurityOntology:
    """
    Lightweight cybersecurity concept graph backed by NetworkX.
    ~300-500 nodes, ~5000-10000 edges. Fully in-memory. CPU-friendly.
    """
    
    HOP1_WEIGHT = 0.8
    HOP2_WEIGHT = 0.5
    MAX_EXPANSION_HOPS = 2
    MAX_EXPANSION_NODES = 10
    
    def __init__(self, ontology_path: Path):
        with open(ontology_path) as f:
            data = json.load(f)
        self.graph: nx.DiGraph = nx.node_link_graph(data, edges="links")
        self._alias_index: dict[str, str] = self._build_alias_index()
    
    def _build_alias_index(self) -> dict[str, str]:
        """Map all aliases and labels to canonical node IDs."""
        index = {}
        for node_id, attrs in self.graph.nodes(data=True):
            index[attrs.get("label", "").lower()] = node_id
            for alias in attrs.get("aliases", []):
                index[alias.lower()] = node_id
        return index
    
    def resolve(self, text: str) -> str | None:
        """Find canonical node ID for a text string."""
        return self._alias_index.get(text.lower().strip())
    
    def expand(self, concept_text: str) -> ConceptExpansion:
        """
        Traverse the graph from a seed concept and return related concepts
        weighted by graph distance.
        """
        seed_id = self.resolve(concept_text)
        if seed_id is None:
            return ConceptExpansion(
                seed_concept=concept_text,
                expanded_concepts=[],
                traversal_path=[]
            )
        
        expanded = {}
        queue = [(seed_id, 0, [seed_id])]
        visited = {seed_id}
        
        while queue:
            node, hop, path = queue.pop(0)
            if hop > self.MAX_EXPANSION_HOPS:
                continue
            
            weight = 1.0 if hop == 0 else (self.HOP1_WEIGHT if hop == 1 else self.HOP2_WEIGHT)
            expanded[node] = max(expanded.get(node, 0), weight)
            
            if len(expanded) >= self.MAX_EXPANSION_NODES:
                break
            
            for neighbor in list(self.graph.predecessors(node)) + list(self.graph.successors(node)):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, hop + 1, path + [neighbor]))
        
        result = []
        for node_id, weight in sorted(expanded.items(), key=lambda x: -x[1]):
            if node_id != seed_id:
                label = self.graph.nodes[node_id].get("label", node_id)
                aliases = self.graph.nodes[node_id].get("aliases", [])
                result.append((label, weight, aliases))
        
        return ConceptExpansion(
            seed_concept=concept_text,
            expanded_concepts=[(label, weight) for label, weight, _ in result],
            traversal_path=[]
        )
    
    def get_related_terms(self, concept_text: str) -> list[str]:
        expansion = self.expand(concept_text)
        terms = [concept_text]
        for concept_label, weight in expansion.expanded_concepts:
            terms.append(concept_label)
            node_id = self.resolve(concept_label)
            if node_id:
                aliases = self.graph.nodes[node_id].get("aliases", [])
                terms.extend(aliases[:2] if weight >= self.HOP1_WEIGHT else aliases[:1])
        return terms
    
    @lru_cache(maxsize=256)
    def get_domain(self, concept_text: str) -> str | None:
        node_id = self.resolve(concept_text)
        if node_id:
            return self.graph.nodes[node_id].get("domain")
        return None
    
    def are_related(self, concept_a: str, concept_b: str) -> bool:
        id_a = self.resolve(concept_a)
        id_b = self.resolve(concept_b)
        if not id_a or not id_b:
            return False
        try:
            path = nx.shortest_path(self.graph.to_undirected(), id_a, id_b)
            return len(path) <= 4
        except nx.NetworkXNoPath:
            return False

_ontology_instance: SecurityOntology | None = None

def get_ontology(path: Path | None = None) -> SecurityOntology:
    global _ontology_instance
    if _ontology_instance is None:
        if path is None:
            path = Path(__file__).parent.parent.parent / "knowledge_base" / "ontology.json"
        _ontology_instance = SecurityOntology(path)
    return _ontology_instance
