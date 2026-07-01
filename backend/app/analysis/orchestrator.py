from typing import List, Dict, Any
import asyncio
import json
import os

from app.schemas.assessment import AssessmentResultCreate
from app.schemas.capability import CapabilityObject
from app.analysis.tier1_semantic import Tier1Semantic
from app.analysis.tier2_capability import Tier2Capability
from app.analysis.evidence_quality import EvidenceQualityAssessor
from app.analysis.negation_detector import NegationDetector
from app.analysis.tier3_llm import Tier3LLM
from app.analysis.grounding_verifier import GroundingVerifier
from app.analysis.prohibition import ProhibitionAnalyser
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.query_expander import QueryExpander
from app.retrieval.reranker import Reranker


class AssessmentOrchestrator:
    """
    Enterprise-style compliance orchestrator.

    The final decision blends retrieval semantic strength, structured capability
    coverage, evidence quality, prohibition checks, LLM reasoning, and grounding.
    """

    ECHO_OVERLAP_THRESHOLD = 0.55

    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever
        self.child_concurrency = max(1, int(os.getenv("ASSESSMENT_CHILD_CONCURRENCY", "3")))
        self.expander = QueryExpander()
        self.reranker = Reranker()
        self.tier1 = Tier1Semantic(embedder=self.retriever.embedder)
        self.tier2 = Tier2Capability()
        self.quality = EvidenceQualityAssessor()
        self.negation = NegationDetector()
        self.tier3 = Tier3LLM()
        self.grounding = GroundingVerifier()
        self.prohibition = ProhibitionAnalyser()

    def _build_retrieval_query(self, requirement: Dict[str, Any]) -> str:
        title = requirement.get("title", "")
        keywords = requirement.get("keywords", []) or requirement.get("mandatory_concepts", [])
        if keywords:
            expanded = []
            for kw in keywords[:5]:
                expanded.extend(self.expander.expand(kw)[:4])
            terms = list(dict.fromkeys(expanded))
            return " ".join(([title] if title else []) + terms)
        return f"{title} {requirement.get('text', '')[:240]}".strip()

    def _token_overlap(self, text_a: str, text_b: str) -> float:
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())
        if not tokens_a:
            return 0.0
        return len(tokens_a & tokens_b) / len(tokens_a)

    def _filter_requirement_echoes(self, chunks: List[Dict[str, Any]], requirement_text: str) -> List[Dict[str, Any]]:
        filtered = []
        for chunk in chunks:
            chunk_text = chunk.get("payload", {}).get("text", "")
            if self._token_overlap(requirement_text, chunk_text) < self.ECHO_OVERLAP_THRESHOLD:
                filtered.append(chunk)
        return filtered

    def _is_undertaking_requirement(self, requirement_text: str) -> bool:
        lower = requirement_text.lower()
        return (
            "undertaking" in lower
            or "self declaration" in lower
            or "self-declaration" in lower
        )

    def _is_prohibition_requirement(self, requirement: Dict[str, Any]) -> bool:
        if requirement.get("is_prohibition"):
            return True
        lower = requirement.get("text", "").lower()
        return "shall not" in lower or "must not" in lower or "not support" in lower

    def _mandatory_concepts(self, requirement: Dict[str, Any], expected_caps: List[CapabilityObject]) -> List[str]:
        concepts = []
        concepts.extend(requirement.get("mandatory_concepts", []))
        concepts.extend(requirement.get("keywords", []))
        concepts.extend([cap.concept for cap in expected_caps])
        return list(dict.fromkeys([c for c in concepts if c]))

    def _prohibition_keywords(
        self,
        requirement: Dict[str, Any],
        expected_caps: List[CapabilityObject],
        mandatory_concepts: List[str],
    ) -> List[str]:
        keywords = []
        keywords.extend(requirement.get("keywords", []))
        keywords.extend([cap.source_text or cap.concept for cap in expected_caps])
        keywords.extend(mandatory_concepts)
        cleaned = []
        cleaned_lower = set()
        for kw in keywords:
            if not kw:
                continue
            text = str(kw).strip()
            lower = text.lower()
            if len(text) >= 2 and lower not in cleaned_lower:
                cleaned.append(text)
                cleaned_lower.add(lower)
        return cleaned[:10]

    def _normalize_status(self, verdict: str | None) -> str:
        verdict_upper = (verdict or "").upper()
        if "NON" in verdict_upper:
            return "non_compliant"
        if "COMPLIANT" in verdict_upper and "NON" not in verdict_upper:
            return "compliant"
        if "PARTIAL" in verdict_upper:
            return "partial"
        return "manual_review"

    def _calculate_confidence(
        self,
        semantic_score: float,
        capability_score: float,
        evidence_quality_score: float,
        grounding_score: float,
        llm_status: str,
        final_status: str,
    ) -> float:
        llm_alignment = 1.0 if llm_status == final_status else 0.6 if llm_status in {"partial", "manual_review"} else 0.35
        score = (
            0.30 * semantic_score
            + 0.25 * capability_score
            + 0.20 * evidence_quality_score
            + 0.15 * grounding_score
            + 0.10 * llm_alignment
        )
        return max(0.0, min(1.0, round(score, 3)))

    def _build_fallback_evidence(self, evidence_chunks: List[Dict[str, Any]]) -> List[str]:
        evidence = []
        for chunk in evidence_chunks[:3]:
            text = chunk.get("payload", {}).get("text", "").strip()
            if text:
                evidence.append(text[:220] + ("..." if len(text) > 220 else ""))
        return evidence

    def _build_consistent_summary(
        self,
        final_status: str,
        matched_concepts: List[str],
        missing_concepts: List[str],
        evidence_chunks: List[Dict[str, Any]],
        llm_result: Dict[str, Any],
        prohibition_details: Dict[str, Any] | None,
    ) -> str:
        matched_preview = ", ".join(matched_concepts[:4]) if matched_concepts else "no key requirement concepts"
        missing_preview = ", ".join(missing_concepts[:4]) if missing_concepts else "no uncovered concepts"
        evidence_count = len(evidence_chunks)
        llm_summary = (llm_result.get("justification") or "").strip()

        if final_status == "compliant":
            base = (
                f"Analysis confirms compliance. "
                f"The product architecture securely implements {matched_preview}."
            )
            if prohibition_details and prohibition_details.get("violations") == []:
                base += " Verification confirms the absence of prohibited features or insecure configurations."
            return base

        if final_status == "partial":
            base = (
                f"Analysis indicates partial compliance. While the product successfully demonstrates capability for {matched_preview}, "
                f"there is a critical gap regarding the implementation of {missing_preview}."
            )
            return base

        if final_status == "non_compliant":
            if prohibition_details and prohibition_details.get("violations"):
                violations = ", ".join(prohibition_details["violations"][:4])
                return (
                    f"Analysis concludes non-compliance. The product exhibits prohibited behaviors or insecure implementations: {violations}."
                )
            base = (
                f"Analysis concludes non-compliance due to a lack of demonstrable control coverage for {missing_preview}."
            )
            if matched_concepts:
                base += f" Although mechanisms for {matched_preview} are present, they fail to meet the comprehensive security baseline required."
            return base

        if final_status == "evidence_not_found":
            return (
                "Unable to verify compliance. The provided documentation lacks the necessary technical depth or architectural evidence required to assess this control."
            )

        if final_status == "manual_review":
            return llm_summary or "This requirement requires manual review."

        return "Assessment completed."

    def _enforce_status_consistency(
        self,
        final_status: str,
        llm_status: str,
        mandatory_concepts: List[str],
        matched_concepts: List[str],
        missing_concepts: List[str],
        semantic_score: float,
        capability_score: float,
        evidence_quality_score: float,
        evidence_chunks: List[Dict[str, Any]],
    ) -> tuple[str, List[str], List[str]]:
        matched = list(dict.fromkeys([c for c in matched_concepts if c]))
        missing = list(dict.fromkeys([c for c in missing_concepts if c]))
        mandatory = list(dict.fromkeys([c for c in mandatory_concepts if c]))

        if final_status == "compliant":
            unresolved = [c for c in missing if c.lower() not in {m.lower() for m in matched}]
            if unresolved:
                has_strong_evidence = semantic_score >= 0.7 and capability_score >= 0.9 and evidence_quality_score >= 0.8
                if not has_strong_evidence or llm_status in {"partial", "non_compliant"}:
                    final_status = "partial"
                    missing = unresolved
            if final_status == "compliant":
                missing = []
                if mandatory:
                    matched = list(dict.fromkeys(matched + mandatory))

        elif final_status == "evidence_not_found":
            if evidence_chunks and (semantic_score >= 0.35 or capability_score >= 0.35 or llm_status in {"compliant", "partial"}):
                final_status = "partial"
            else:
                matched = []

        elif final_status == "non_compliant":
            if evidence_chunks and matched and not missing and llm_status == "compliant":
                final_status = "partial"
                missing = [c for c in mandatory if c.lower() not in {m.lower() for m in matched}] or ["full control coverage"]

        if final_status == "partial":
            if not matched and mandatory:
                matched = [mandatory[0]] if semantic_score >= 0.35 or capability_score >= 0.35 else []
            if not missing:
                missing = [c for c in mandatory if c.lower() not in {m.lower() for m in matched}]
            if not missing:
                missing = ["complete control coverage"]

        return final_status, matched, missing

    def _build_consistent_recommendation(
        self,
        final_status: str,
        missing_concepts: List[str],
        prohibition_details: Dict[str, Any] | None,
        llm_result: Dict[str, Any],
    ) -> str:
        llm_recommendation = (llm_result.get("recommendation") or "").strip()
        if final_status == "compliant":
            return "Retain the cited evidence in the audit trail for this requirement."
        if final_status == "partial":
            if missing_concepts:
                return f"Add explicit product evidence for: {', '.join(missing_concepts[:4])}."
            return llm_recommendation or "Add stronger product evidence to close the remaining coverage gaps."
        if final_status == "non_compliant":
            if prohibition_details and prohibition_details.get("violations"):
                return f"Remove, disable, or clearly exclude: {', '.join(prohibition_details['violations'][:4])}."
            if missing_concepts:
                return f"Provide implementation evidence or remediation for: {', '.join(missing_concepts[:4])}."
            return llm_recommendation or "Remediate the missing control implementation and provide supporting evidence."
        if final_status == "evidence_not_found":
            return "Provide a security target, configuration guide, or test evidence that directly addresses this requirement."
        return llm_recommendation or "Review this requirement manually."

    async def _assess_child(self, child: Dict[str, Any]) -> AssessmentResultCreate:
        requirement_id = child.get("id", "Unknown")
        requirement_title = child.get("title", requirement_id)
        requirement_text = child.get("text", "")

        if self._is_undertaking_requirement(requirement_text):
            payload = {
                "verdict": "MANUAL-REVIEW",
                "summary": "This requirement depends on an OEM undertaking or self-declaration rather than product evidence alone.",
                "recommendation": "Obtain and validate the signed undertaking artifact from the vendor.",
                "decision_basis": "undertaking_fast_path",
                "scores": {},
                "expected_capabilities": [],
                "observed_capabilities": [],
                "matched_concepts": [],
                "missing_concepts": [],
                "evidence_excerpt_count": 0,
                "extracted_evidence": [],
            }
            return AssessmentResultCreate(
                requirement_id=requirement_id,
                status="manual_review",
                confidence_score=1.0,
                justification=json.dumps(payload),
                evidence_references=[],
                analysis_details=payload,
            )

        expected_capabilities = self.tier2.extractor.extract(requirement_text)
        mandatory_concepts = self._mandatory_concepts(child, expected_capabilities)
        child["mandatory_concepts"] = mandatory_concepts

        query = self._build_retrieval_query(child)
        candidate_chunks = self.retriever.retrieve(query, top_k=20)
        reranked = self.reranker.rerank(query, candidate_chunks, top_k=8) if candidate_chunks else []
        evidence_chunks = self._filter_requirement_echoes(reranked, requirement_text)

        semantic_score = self.tier1.compute_score(evidence_chunks)
        semantic_quality = self.tier1.compute_quality(child, evidence_chunks)
        evidence_quality_score = self.quality.assess(evidence_chunks)
        capability_score, observed_caps, missing_caps = self.tier2.analyze(expected_capabilities, evidence_chunks)

        llm_result = await self.tier3.analyze_requirement(requirement_title, requirement_text, evidence_chunks)
        llm_status = self._normalize_status(llm_result.get("verdict"))
        grounding_score = self.grounding.verify(llm_result.get("justification", ""), evidence_chunks)

        matched_concepts = list(dict.fromkeys(
            [str(c) for c in llm_result.get("matched_concepts", []) if c]
            + [cap.concept for cap in expected_capabilities if cap not in missing_caps]
        ))
        missing_concepts = list(dict.fromkeys(
            [str(c) for c in llm_result.get("missing_concepts", []) if c]
            + [cap.concept for cap in missing_caps]
        ))

        prohibition_details = None
        if self._is_prohibition_requirement(child):
            prohibition_keywords = self._prohibition_keywords(child, expected_capabilities, mandatory_concepts)
            prohibition_ok, violations = self.prohibition.analyze(prohibition_keywords, evidence_chunks)
            prohibition_details = {"keywords": prohibition_keywords, "violations": violations}
            if not evidence_chunks:
                final_status = "evidence_not_found"
            elif prohibition_ok:
                final_status = "compliant"
            else:
                final_status = "non_compliant"
                missing_concepts = list(dict.fromkeys(missing_concepts + violations))
        else:
            if not evidence_chunks or semantic_quality["quality"] == "Low":
                final_status = "evidence_not_found"
            elif capability_score >= 0.80 and semantic_score >= 0.40 and grounding_score >= 0.40:
                final_status = "compliant"
            elif capability_score >= 0.45 or semantic_score >= 0.28 or llm_status == "partial":
                final_status = "partial"
            elif llm_status == "compliant" and evidence_quality_score >= 0.75 and grounding_score >= 0.40:
                final_status = "compliant"
            else:
                final_status = "non_compliant"

        final_status, matched_concepts, missing_concepts = self._enforce_status_consistency(
            final_status,
            llm_status,
            mandatory_concepts,
            matched_concepts,
            missing_concepts,
            semantic_score,
            capability_score,
            evidence_quality_score,
            evidence_chunks,
        )

        confidence = self._calculate_confidence(
            semantic_score,
            capability_score,
            evidence_quality_score,
            grounding_score,
            llm_status,
            final_status,
        )

        extracted_evidence = llm_result.get("extracted_evidence", []) or self._build_fallback_evidence(evidence_chunks)
        summary = self._build_consistent_summary(
            final_status,
            matched_concepts,
            missing_concepts,
            evidence_chunks,
            llm_result,
            prohibition_details,
        )
        recommendation = self._build_consistent_recommendation(
            final_status,
            missing_concepts,
            prohibition_details,
            llm_result,
        )

        payload = {
            "verdict": final_status.upper().replace("_", "-"),
            "justification": summary,
            "summary": summary,
            "recommendation": recommendation,
            "decision_basis": "multi_signal_orchestrator",
            "scores": {
                "semantic": round(semantic_score, 3),
                "capability": round(capability_score, 3),
                "evidence_quality": round(evidence_quality_score, 3),
                "grounding": round(grounding_score, 3),
                "confidence": confidence,
                "retrieval_quality": semantic_quality,
            },
            "expected_capabilities": [cap.model_dump() for cap in expected_capabilities],
            "observed_capabilities": [cap.model_dump() for cap in observed_caps],
            "matched_concepts": matched_concepts,
            "missing_concepts": missing_concepts,
            "evidence_excerpt_count": len(evidence_chunks),
            "extracted_evidence": extracted_evidence,
            "llm_verdict": llm_result.get("verdict"),
            "is_prohibition_requirement": self._is_prohibition_requirement(child),
            "prohibition_details": prohibition_details,
        }

        evidence_refs = [chunk.get("id") for chunk in evidence_chunks[:4] if chunk.get("id")]
        return AssessmentResultCreate(
            requirement_id=requirement_id,
            status=final_status,
            confidence_score=confidence,
            justification=json.dumps(payload),
            evidence_references=evidence_refs,
            analysis_details=payload,
        )

    async def assess_group(
        self,
        group: Dict[str, Any],
        children: List[Dict[str, Any]],
        progress_callback=None,
    ) -> List[AssessmentResultCreate]:
        group_id = "GROUP-" + group.get("id", "Unknown")
        group_title = group.get("title", group.get("id", "Unknown"))

        child_results: List[AssessmentResultCreate] = []
        child_sem = asyncio.Semaphore(self.child_concurrency)

        async def process_child(index: int, child: Dict[str, Any]):
            async with child_sem:
                result = await self._assess_child(child)
                if progress_callback:
                    await progress_callback(result)
                return index, result

        if children:
            ordered_results = await asyncio.gather(
                *(process_child(index, child) for index, child in enumerate(children))
            )
            ordered_results.sort(key=lambda item: item[0])
            child_results = [result for _, result in ordered_results]

        status_counts = {
            "compliant": 0,
            "partial": 0,
            "non_compliant": 0,
            "manual_review": 0,
            "evidence_not_found": 0,
        }
        total_confidence = 0.0
        all_evidence = []
        missing_requirements = []
        for result in child_results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
            total_confidence += result.confidence_score
            for evidence_ref in result.evidence_references:
                if evidence_ref not in all_evidence:
                    all_evidence.append(evidence_ref)
            if result.status in {"non_compliant", "evidence_not_found", "partial"}:
                missing_requirements.append(result.requirement_id)

        if not child_results:
            group_status = "manual_review"
        elif status_counts["non_compliant"] > 0:
            group_status = "non_compliant"
        elif status_counts["evidence_not_found"] > 0 and status_counts["compliant"] == 0:
            group_status = "evidence_not_found"
        elif status_counts["partial"] > 0 or status_counts["manual_review"] > 0 or status_counts["evidence_not_found"] > 0:
            group_status = "partial"
        else:
            group_status = "compliant"

        coverage_ratio = (
            status_counts["compliant"] + (0.5 * status_counts["partial"])
        ) / max(1, len(child_results))
        group_payload = {
            "verdict": group_status.upper().replace("_", "-"),
            "summary": f"Section {group.get('id', 'Unknown')} - {group_title} has been assessed using {len(child_results)} child requirement(s).",
            "recommendation": "Prioritize remediation and evidence review for the child requirements marked non-compliant, partially covered, or evidence not found.",
            "decision_basis": "section_rollup",
            "section_id": group.get("id", "Unknown"),
            "section_name": group_title,
            "scores": {
                "coverage_ratio": round(coverage_ratio, 3),
                "average_child_confidence": round(total_confidence / max(1, len(child_results)), 3),
            },
            "status_counts": status_counts,
            "missing_requirements": missing_requirements,
        }
        group_result = AssessmentResultCreate(
            requirement_id=group_id,
            status=group_status,
            confidence_score=round(total_confidence / max(1, len(child_results)), 3) if child_results else 0.0,
            justification=json.dumps(group_payload),
            evidence_references=all_evidence[:10],
            analysis_details=group_payload,
        )

        if progress_callback:
            await progress_callback(group_result)

        return child_results + [group_result]

    async def assess_requirement(self, requirement: Dict[str, Any]) -> AssessmentResultCreate:
        return await self._assess_child(requirement)
