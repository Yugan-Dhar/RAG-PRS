from typing import List, Dict, Any
import logging
import asyncio
import json
import hashlib
import os
from pathlib import Path

logger = logging.getLogger(__name__)

OLLAMA_LOCK = None


class Tier3LLM:
    """
    Uses a local Ollama model to produce structured gap-analysis output.
    The orchestrator treats this as one signal among several, not the sole judge.
    """

    CACHE_VERSION = "v1"

    def __init__(
        self,
        host: str = "http://127.0.0.1:11434",
        model: str = "llama3.2:latest",
        cache_dir: str | None = None,
    ):
        self.host = host
        self.model = model
        self.options = {"temperature": 0.0, "num_predict": 700, "num_ctx": 4096}
        default_cache_dir = Path(__file__).resolve().parents[2] / ".rag_store" / "llm_cache"
        self.cache_dir = Path(cache_dir) if cache_dir else default_cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            import requests
            self.requests = requests
        except ImportError:
            self.requests = None

    def _call_ollama_sync(self, prompt: str) -> str:
        response = self.requests.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": self.options,
            },
            timeout=180,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def _build_gap_analysis_prompt(
        self,
        requirement_title: str,
        requirement_text: str,
        evidence_chunks: List[Dict[str, Any]],
    ) -> str:
        context_parts = []
        for i, chunk in enumerate(evidence_chunks[:5]):
            text = chunk.get("payload", {}).get("text", "").strip()
            chunk_id = chunk.get("id", f"excerpt-{i + 1}")
            if text:
                context_parts.append(f"[{chunk_id}] {text[:500]}")
        context = "\n\n".join(context_parts) if context_parts else "No relevant excerpts found."

        return (
            "You are an enterprise security compliance gap analyst.\n"
            "Assess the requirement using only the supplied excerpts.\n\n"
            f"REQUIREMENT TITLE: {requirement_title}\n"
            f"REQUIREMENT TEXT: {requirement_text}\n\n"
            f"EVIDENCE EXCERPTS:\n{context}\n\n"
            "GUIDELINES FOR JUSTIFICATION:\n"
            "- Write a concise explanation in 2-3 natural sentences.\n"
            "- Start by describing what the requirement expects.\n"
            "- Summarize only the capabilities explicitly supported by the evidence.\n"
            "- Identify any required capability not demonstrated.\n"
            "- Never infer unsupported functionality.\n"
            "- Avoid generic phrases ('analysis indicates', 'the product is compliant').\n"
            "- Do not repeat the verdict or confidence score.\n"
            "- Vary your sentence structure naturally depending on the evidence. Use flexible wording like:\n"
            "  * 'The requirement expects [X]. The documentation describes [Y], but does not explicitly demonstrate [Z].'\n"
            "  * 'The documentation confirms [Y]. However, no explicit evidence was found for [Z].'\n"
            "  * 'While the documentation covers [Y], additional evidence is needed to verify [Z].'\n"
            "  * 'The documentation provides evidence of [Y].'\n\n"
            "Return exactly one valid JSON object with these keys:\n"
            "{\n"
            '  "concept_analysis": [\n'
            '    {"concept": "mandatory concept from requirement", "status": "evidenced or missing", "excerpt": "relevant evidence snippet if found"}\n'
            '  ],\n'
            '  "verdict": "COMPLIANT" or "PARTIAL" or "NON-COMPLIANT",\n'
            '  "extracted_evidence": ["short direct evidence statements copied or paraphrased from excerpts"],\n'
            '  "matched_concepts": ["requirement concepts that are evidenced"],\n'
            '  "missing_concepts": ["requirement concepts that are not evidenced"],\n'
            '  "justification": "Your 2-3 sentence explanation following the GUIDELINES FOR JUSTIFICATION, derived from your concept_analysis.",\n'
            '  "recommendation": "single next action for compliance officer"\n'
            "}\n"
            "Do not include markdown or any extra text."
        )

    def _cache_key(self, prompt: str) -> str:
        payload = {
            "cache_version": self.CACHE_VERSION,
            "model": self.model,
            "options": self.options,
            "prompt": prompt,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()

    def _cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def _read_cache(self, cache_key: str) -> Dict[str, Any] | None:
        cache_path = self._cache_path(cache_key)
        if not cache_path.exists():
            return None
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Ignoring unreadable LLM cache entry %s: %s", cache_path, exc)
            return None

    def _write_cache(self, cache_key: str, payload: Dict[str, Any]) -> None:
        cache_path = self._cache_path(cache_key)
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=True, sort_keys=True),
            encoding="utf-8",
        )

    async def analyze_requirement(
        self,
        requirement_title: str,
        requirement_text: str,
        evidence_chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not self.requests:
            return {
                "verdict": "PARTIAL",
                "extracted_evidence": [],
                "matched_concepts": [],
                "missing_concepts": [],
                "justification": "LLM client library not installed; final reasoning fell back to rule-based scoring.",
                "recommendation": "Install requests and verify Ollama connectivity.",
                "verdict_bool": None,
            }

        if not evidence_chunks:
            return {
                "verdict": "NON-COMPLIANT",
                "extracted_evidence": [],
                "matched_concepts": [],
                "missing_concepts": ["No evidence retrieved"],
                "justification": "No relevant evidence chunks were retrieved for this requirement.",
                "recommendation": "Provide stronger product evidence or broaden retrieval coverage.",
                "verdict_bool": False,
            }

        prompt = self._build_gap_analysis_prompt(requirement_title, requirement_text, evidence_chunks)
        cache_key = self._cache_key(prompt)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        try:
            global OLLAMA_LOCK
            if OLLAMA_LOCK is None:
                OLLAMA_LOCK = asyncio.Lock()
                
            loop = asyncio.get_event_loop()
            async with OLLAMA_LOCK:
                answer = await loop.run_in_executor(None, self._call_ollama_sync, prompt)
            parsed = json.loads(answer)
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            parsed = {
                "verdict": "PARTIAL",
                "extracted_evidence": [],
                "matched_concepts": [],
                "missing_concepts": [],
                "justification": f"LLM unavailable or malformed output: {exc}",
                "recommendation": "Review evidence manually and restore local LLM service.",
            }

        verdict = str(parsed.get("verdict", "")).upper()
        if "NON" in verdict:
            verdict_bool = False
        elif "COMPLIANT" in verdict and "NON" not in verdict:
            verdict_bool = True
        else:
            verdict_bool = None

        parsed.setdefault("extracted_evidence", [])
        parsed.setdefault("matched_concepts", [])
        parsed.setdefault("missing_concepts", [])
        parsed.setdefault("justification", "")
        parsed.setdefault("recommendation", "")
        parsed["verdict_bool"] = verdict_bool
        try:
            self._write_cache(cache_key, parsed)
        except Exception as exc:
            logger.warning("Failed to persist LLM cache entry: %s", exc)
        return parsed
