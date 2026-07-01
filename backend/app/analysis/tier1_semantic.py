from typing import List, Dict, Any
import math
import numpy as np


class Tier1Semantic:
    """
    Tier 1 semantic scoring for retrieval quality and evidence sufficiency.
    """

    def __init__(self, semantic_threshold: float = 0.20, embedder=None):
        self.semantic_threshold = semantic_threshold
        self.embedder = embedder
        from app.knowledge.ontology import get_ontology
        self.ontology = get_ontology()

    def compute_score(self, evidence_chunks: List[Dict[str, Any]]) -> float:
        if not evidence_chunks:
            return 0.0

        scores = []
        for chunk in evidence_chunks:
            if "cosine_score" in chunk:
                scores.append(float(chunk["cosine_score"]))
            elif "rerank_score" in chunk:
                logit = float(chunk["rerank_score"])
                scores.append(1.0 / (1.0 + math.exp(-logit)))
            else:
                scores.append(float(chunk.get("score", 0.0)))

        if not scores:
            return 0.0

        weights = [0.6, 0.3, 0.1]
        weighted_score = 0.0
        weight_sum = 0.0
        for i, score in enumerate(scores[:3]):
            weighted_score += score * weights[i]
            weight_sum += weights[i]
        return max(0.0, min(1.0, weighted_score / weight_sum if weight_sum else 0.0))

    def compute_quality(self, requirement: Dict[str, Any], evidence_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not evidence_chunks:
            return {
                "quality": "Low",
                "metrics": {
                    "average_reranker_score": 0.0,
                    "average_similarity": 0.0,
                    "concept_overlap": 0.0,
                    "composite_score": 0.0,
                },
            }

        cosines = [float(c["cosine_score"]) for c in evidence_chunks if "cosine_score" in c]
        avg_sim = sum(cosines) / len(cosines) if cosines else 0.0

        rerank_scores = []
        for chunk in evidence_chunks:
            if "rerank_score" in chunk:
                logit = float(chunk["rerank_score"])
                rerank_scores.append(1.0 / (1.0 + math.exp(-logit)))
        avg_rerank = sum(rerank_scores) / len(rerank_scores) if rerank_scores else avg_sim

        mandatory_concepts = requirement.get("mandatory_concepts", requirement.get("keywords", []))
        overlap_count = 0
        text = " ".join(c.get("payload", {}).get("text", "").lower() for c in evidence_chunks)

        sentences = []
        sentence_embeddings = None
        if self.embedder and mandatory_concepts:
            import re
            for chunk in evidence_chunks[:3]:
                chunk_text = chunk.get("payload", {}).get("text", "")
                splits = [s.strip() for s in re.split(r"[.!?\n]", chunk_text) if len(s.strip()) > 15]
                sentences.extend(splits[:6])
            if sentences:
                sentence_embeddings = np.array(self.embedder.embed_documents(sentences))

        for concept in mandatory_concepts:
            concept_found = False
            for term in self.ontology.get_related_terms(concept):
                if term.lower() in text:
                    concept_found = True
                    break

            if not concept_found and sentence_embeddings is not None:
                concept_emb = np.array(self.embedder.embed_query(concept))
                sims = np.dot(sentence_embeddings, concept_emb)
                if len(sims) > 0 and float(np.max(sims)) > 0.45:
                    concept_found = True

            if concept_found:
                overlap_count += 1

        concept_overlap = overlap_count / max(1, len(mandatory_concepts))
        composite_score = (0.5 * avg_rerank) + (0.3 * avg_sim) + (0.2 * concept_overlap)

        if composite_score >= 0.35:
            quality = "High"
        elif composite_score >= 0.15:
            quality = "Medium"
        else:
            quality = "Low"

        return {
            "quality": quality,
            "metrics": {
                "average_reranker_score": round(avg_rerank, 3),
                "average_similarity": round(avg_sim, 3),
                "concept_overlap": round(concept_overlap, 3),
                "composite_score": round(composite_score, 3),
            },
        }
