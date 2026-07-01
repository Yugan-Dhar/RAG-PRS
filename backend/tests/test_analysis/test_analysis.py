import pytest
import asyncio
from pathlib import Path
import shutil
import uuid
from app.analysis.tier1_semantic import Tier1Semantic
from app.analysis.evidence_quality import EvidenceQualityAssessor
from app.analysis.negation_detector import NegationDetector
from app.analysis.applicability import ApplicabilityEngine
from app.ingestion.standards.itsar_router_config import ITSARRouterConfig
from app.analysis.orchestrator import AssessmentOrchestrator
from app.analysis.tier3_llm import Tier3LLM
import json


def test_tier1_semantic():
    tier1 = Tier1Semantic()
    chunks = [
        {"cosine_score": 0.8},
        {"rerank_score": 0.6},
        {"score": 0.5},
    ]
    score = tier1.compute_score(chunks)
    assert 0.0 < score <= 1.0


def test_evidence_quality():
    assessor = EvidenceQualityAssessor()
    chunks = [{"payload": {"metadata": {"doc_type": "standard"}}}]
    score = assessor.assess(chunks)
    assert score == 1.0


def test_negation_detector():
    detector = NegationDetector()
    assert detector.detect("The router does not support SSH.", "SSH") is True
    assert detector.detect("The router supports SSH.", "SSH") is False


def test_applicability_filters_children():
    groups = [
        {
            "id": "2.1",
            "children": [
                {"id": "2.1.1", "applicable_router_types": ["conventional"], "required_capability_flags": []},
                {"id": "2.1.2", "applicable_router_types": ["virtual"], "required_capability_flags": []},
            ],
        }
    ]
    config = ITSARRouterConfig(router_type="conventional", capability_flags=[])
    filtered = ApplicabilityEngine.filter_requirements(groups, config)
    assert len(filtered) == 1
    assert [child["id"] for child in filtered[0]["children"]] == ["2.1.1"]


@pytest.mark.asyncio
async def test_orchestrator_summary_aligns_with_final_status():
    class MockRetriever:
        def __init__(self):
            self.embedder = None

        def retrieve(self, query, top_k=20):
            return [{
                "id": "c1",
                "cosine_score": 0.9,
                "score": 0.9,
                "payload": {"text": "The router supports SSH mutual authentication and cryptographic controls."},
            }]

    orchestrator = AssessmentOrchestrator(MockRetriever())
    orchestrator.reranker.rerank = lambda query, chunks, top_k=8: chunks[:top_k]
    orchestrator.tier2.extractor.extract = lambda text: []
    orchestrator.tier2.analyze = lambda expected, evidence: (0.95, [], [])
    orchestrator.quality.assess = lambda evidence: 1.0
    orchestrator.grounding.verify = lambda justification, evidence: 1.0

    async def mock_llm(*args, **kwargs):
        return {
            "verdict": "NON-COMPLIANT",
            "extracted_evidence": ["SSH mutual authentication is supported."],
            "matched_concepts": ["mutual authentication"],
            "missing_concepts": ["table 1 cryptographic controls"],
            "justification": "The evidence appears insufficient.",
            "recommendation": "Provide more evidence.",
        }

    orchestrator.tier3.analyze_requirement = mock_llm

    result = await orchestrator.assess_requirement({
        "id": "2.1.1",
        "title": "Authentication for Product Management and Maintenance interfaces",
        "text": "IP Router shall support mutual authentication on management interfaces.",
        "keywords": ["mutual authentication"],
        "mandatory_concepts": ["mutual authentication"],
    })

    payload = json.loads(result.justification)
    assert result.status == "partial"
    assert payload["verdict"] == "PARTIAL"
    assert "partial" in payload["summary"].lower()
    assert payload["missing_concepts"] == ["table 1 cryptographic controls"]


@pytest.mark.asyncio
async def test_orchestrator_downgrades_compliant_when_gaps_remain():
    class MockRetriever:
        def __init__(self):
            self.embedder = None

        def retrieve(self, query, top_k=20):
            return [{
                "id": "c1",
                "cosine_score": 0.55,
                "score": 0.55,
                "payload": {"text": "The router supports SSH-based administrative access."},
            }]

    orchestrator = AssessmentOrchestrator(MockRetriever())
    orchestrator.reranker.rerank = lambda query, chunks, top_k=8: chunks[:top_k]
    orchestrator.tier2.extractor.extract = lambda text: []
    orchestrator.tier2.analyze = lambda expected, evidence: (0.55, [], [])
    orchestrator.quality.assess = lambda evidence: 0.6
    orchestrator.grounding.verify = lambda justification, evidence: 0.7

    async def mock_llm(*args, **kwargs):
        return {
            "verdict": "COMPLIANT",
            "extracted_evidence": ["Administrative access is supported."],
            "matched_concepts": ["administrative access"],
            "missing_concepts": ["cryptographic controls"],
            "justification": "The product generally addresses the control.",
            "recommendation": "No action required.",
        }

    orchestrator.tier3.analyze_requirement = mock_llm

    result = await orchestrator.assess_requirement({
        "id": "2.1.2",
        "title": "Management Traffic Protection",
        "text": "Management traffic shall be protected using secure cryptographic controls.",
        "keywords": ["management traffic", "cryptographic controls"],
        "mandatory_concepts": ["management traffic", "cryptographic controls"],
    })

    payload = json.loads(result.justification)
    assert result.status == "partial"
    assert payload["verdict"] == "PARTIAL"
    assert payload["missing_concepts"]


@pytest.mark.asyncio
async def test_orchestrator_promotes_evidence_not_found_to_partial_when_some_evidence_exists():
    class MockRetriever:
        def __init__(self):
            self.embedder = None

        def retrieve(self, query, top_k=20):
            return [{
                "id": "c1",
                "cosine_score": 0.45,
                "score": 0.45,
                "payload": {"text": "The router enforces individual user accounts for administrators."},
            }]

    orchestrator = AssessmentOrchestrator(MockRetriever())
    orchestrator.reranker.rerank = lambda query, chunks, top_k=8: chunks[:top_k]
    orchestrator.tier2.extractor.extract = lambda text: []
    orchestrator.tier2.analyze = lambda expected, evidence: (0.4, [], [])
    orchestrator.quality.assess = lambda evidence: 0.5
    orchestrator.grounding.verify = lambda justification, evidence: 0.6

    async def mock_llm(*args, **kwargs):
        return {
            "verdict": "PARTIAL",
            "extracted_evidence": ["Individual administrator accounts are supported."],
            "matched_concepts": ["individual accounts"],
            "missing_concepts": ["group account prohibition"],
            "justification": "Some relevant account-control evidence is present.",
            "recommendation": "Add explicit evidence for group account restrictions.",
        }

    orchestrator.tier3.analyze_requirement = mock_llm
    original_quality = orchestrator.tier1.compute_quality
    orchestrator.tier1.compute_quality = lambda requirement, evidence: {
        "quality": "Low",
        "metrics": {"average_reranker_score": 0.3, "average_similarity": 0.3, "concept_overlap": 0.5, "composite_score": 0.32},
    }

    result = await orchestrator.assess_requirement({
        "id": "2.1.7",
        "title": "Unambiguous identification of the user",
        "text": "Users shall be identified unambiguously and group accounts shall not be enabled.",
        "keywords": ["individual accounts", "group accounts"],
        "mandatory_concepts": ["individual accounts", "group accounts"],
    })

    payload = json.loads(result.justification)
    assert result.status == "partial"
    assert payload["verdict"] == "PARTIAL"
    assert "partial" in payload["summary"].lower()


@pytest.mark.asyncio
async def test_tier3_llm_uses_disk_cache():
    cache_root = Path(".tmp_test_llm_cache") / str(uuid.uuid4())
    llm = Tier3LLM(cache_dir=str(cache_root))
    llm.requests = object()
    calls = {"count": 0}

    def mock_call(prompt: str) -> str:
        calls["count"] += 1
        return json.dumps({
            "verdict": "COMPLIANT",
            "extracted_evidence": ["SSH is enabled."],
            "matched_concepts": ["ssh"],
            "missing_concepts": [],
            "justification": "SSH-based management access is described in the supplied evidence.",
            "recommendation": "Retain the cited evidence.",
        })

    llm._call_ollama_sync = mock_call
    evidence = [{"id": "c1", "payload": {"text": "SSH is enabled for management access."}}]

    first = await llm.analyze_requirement("Req", "Use SSH", evidence)
    second = await llm.analyze_requirement("Req", "Use SSH", evidence)

    assert calls["count"] == 1
    assert first == second
    assert list(cache_root.glob("*.json"))
    shutil.rmtree(cache_root, ignore_errors=True)


@pytest.mark.asyncio
async def test_assess_group_preserves_requirement_order_under_parallelism(monkeypatch):
    class MockRetriever:
        def __init__(self):
            self.embedder = None

    monkeypatch.setenv("ASSESSMENT_CHILD_CONCURRENCY", "3")
    orchestrator = AssessmentOrchestrator(MockRetriever())

    async def mock_assess_child(child):
        delays = {"2.1.1": 0.03, "2.1.2": 0.01, "2.1.3": 0.02}
        await asyncio.sleep(delays[child["id"]])
        return type("Result", (), {
            "requirement_id": child["id"],
            "status": "compliant",
            "confidence_score": 0.9,
            "justification": json.dumps({"summary": child["id"]}),
            "evidence_references": [],
            "analysis_details": {"summary": child["id"]},
        })()

    orchestrator._assess_child = mock_assess_child
    children = [{"id": "2.1.1"}, {"id": "2.1.2"}, {"id": "2.1.3"}]

    results = await orchestrator.assess_group({"id": "2.1", "title": "Section"}, children)

    assert [result.requirement_id for result in results[:3]] == ["2.1.1", "2.1.2", "2.1.3"]
