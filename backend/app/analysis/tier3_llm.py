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

    CACHE_VERSION = "v5"

    def __init__(
        self,
        host: str = "http://127.0.0.1:11434",
        model: str = "llama3.2:latest",
        cache_dir: str | None = None,
    ):
        self.host = host
        self.model = model
        self.options = {"temperature": 0.0, "num_predict": 800, "num_ctx": 4096}
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
            timeout=600,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def _build_gap_analysis_prompt(
        self,
        requirement_title: str,
        requirement_text: str,
        evidence_chunks: List[Dict[str, Any]],
        capability_ledger: Dict[str, Any] = None,
        expected_capabilities: List[str] = None
    ) -> str:
        context_parts = []
        for i, chunk in enumerate(evidence_chunks[:5]):
            text = chunk.get("payload", {}).get("text", "").strip()
            chunk_id = chunk.get("id", f"excerpt-{i + 1}")
            if text:
                context_parts.append(f"[{chunk_id}] {text[:500]}")
        context = "\n\n".join(context_parts) if context_parts else "No relevant excerpts found."

        ledger_section = ""
        if capability_ledger:
            ledger_json = json.dumps(capability_ledger, indent=2)
            ledger_section = (
                f"GLOBAL PRODUCT FACTS:\n"
                f"The following capabilities have been globally confirmed for this product:\n"
                f"{ledger_json}\n"
                f"Use these facts to supplement the excerpts if the excerpts alone are incomplete.\n\n"
            )

        checklist_section = ""
        if expected_capabilities:
            checklist_section = (
                f"EXPECTED CAPABILITIES CHECKLIST:\n"
                f"Ensure you evaluate the evidence against these specific required capabilities:\n"
                f"{json.dumps(expected_capabilities)}\n\n"
            )

        return (
            "You are an enterprise security compliance gap analyst.\n"
            "Assess the requirement using only the supplied excerpts and global facts.\n\n"
            f"REQUIREMENT TITLE: {requirement_title}\n"
            f"REQUIREMENT TEXT: {requirement_text}\n\n"
            f"{checklist_section}"
            f"EVIDENCE EXCERPTS:\n{context}\n\n"
            f"{ledger_section}"
            "VERDICT GUIDELINES:\n"
            "- COMPLIANT: ALL sub-clauses of the requirement are fully satisfied by evidence.\n"
            "- PARTIAL: The evidence satisfies SOME sub-clauses but NOT ALL. Even if most are covered, "
            "use PARTIAL if any sub-clause lacks evidence or has a gap. List the specific gaps.\n"
            "- NON-COMPLIANT: The evidence contradicts the requirement or no sub-clause is satisfied.\n\n"
            "CRITICAL RULES:\n"
            "- If your justification mentions ANY missing evidence, lack of information, or gaps, you MUST return PARTIAL or NON-COMPLIANT, never COMPLIANT.\n"
            "- If the requirement mentions an OEM undertaking or self-declaration, still assess the "
            "product-testable parts of the requirement against the evidence. Note that the undertaking "
            "is a separate artifact that must be verified independently.\n"
            "- Break the requirement into individual sub-clauses and evaluate each one.\n"
            "- A requirement with 5 sub-clauses where 4 are met is PARTIAL, not COMPLIANT.\n"
            "- Identify specific gaps: which sub-clause is missing evidence?\n\n"
            "GUIDELINES FOR JUSTIFICATION:\n"
            "- Write a concise explanation in 2-3 natural sentences.\n"
            "- Start by describing what the requirement expects.\n"
            "- Summarize only the capabilities explicitly supported by the evidence.\n"
            "- Identify any required capability not demonstrated.\n"
            "- Never infer unsupported functionality.\n"
            "- Avoid generic phrases ('analysis indicates', 'the product is compliant').\n"
            "- Do not repeat the verdict or confidence score.\n"
            "- Vary your sentence structure naturally depending on the evidence.\n\n"
            "Return exactly one valid JSON object with these keys:\n"
            "{\n"
            '  "concept_analysis": [\n'
            '    {"concept": "mandatory concept from requirement", "status": "evidenced, absent, or uncertain", "excerpt": "relevant evidence snippet if found"}\n'
            '  ],\n'
            '  "verdict": "COMPLIANT" or "PARTIAL" or "NON-COMPLIANT",\n'
            '  "gaps": ["specific sub-clause or capability that lacks evidence"],\n'
            '  "extracted_evidence": ["short direct evidence statements copied or paraphrased from excerpts"],\n'
            '  "matched_concepts": ["requirement concepts that are evidenced"],\n'
            '  "missing_concepts": ["requirement concepts that are explicitly confirmed as absent or contradicted by evidence"],\n'
            '  "uncertain_concepts": ["requirement concepts that are expected but neither confirmed nor contradicted (i.e. documentation is silent)"],\n'
            '  "justification": "Your 2-3 sentence explanation following the GUIDELINES FOR JUSTIFICATION, derived from your concept_analysis.",\n'
            '  "recommendation": "single next action for compliance officer"\n'
            "}\n"
            "Keep all arrays (extracted_evidence, matched_concepts, missing_concepts, uncertain_concepts, gaps) to a maximum of 5 concise items.\n"
            "CRITICAL: Do not include markdown (like ```json), backticks, or any extra text outside the JSON object.\n"
            "CRITICAL: Never use unescaped double quotes inside the string values. Use single quotes for inner quotes."
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
        capability_ledger: Dict[str, Any] = None,
        expected_capabilities: List[str] = None
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

        prompt = self._build_gap_analysis_prompt(requirement_title, requirement_text, evidence_chunks, capability_ledger, expected_capabilities)
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
                
            import re
            match = re.search(r'\{.*\}', answer, re.DOTALL)
            if match:
                answer = match.group(0)
            
            try:
                parsed = json.loads(answer)
            except json.JSONDecodeError:
                # Attempt to fix unescaped inner quotes by finding quotes that are not near structural characters
                # This is a crude but often effective heuristic for small LLMs
                fixed_answer = re.sub(r'(?<![\[\{\:,]\s)"(?![\s\}\],])', r"'", answer)
                try:
                    parsed = json.loads(fixed_answer)
                except Exception:
                    # Last resort: just extract verdict with regex
                    logger.warning("Could not repair JSON. Falling back to regex extraction.")
                    verdict_match = re.search(r'"verdict"\s*:\s*"([^"]+)"', answer, re.IGNORECASE)
                    verdict = verdict_match.group(1).upper() if verdict_match else "ANALYSIS_FAILED"
                    parsed = {
                        "verdict": verdict,
                        "justification": "Extracted via regex due to malformed JSON.",
                    }
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            parsed = {
                "verdict": "ANALYSIS_FAILED",
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
        
        # Post-hoc consistency check
        if capability_ledger and parsed.get("missing_concepts"):
            # A simple programmatic check: if any missing concept substring matches a ledger value
            # e.g. "SSH" is in missing_concepts, but ledger has "SSHv2"
            flat_ledger = " ".join(
                [str(v) for sublist in capability_ledger.values() if isinstance(sublist, list) for v in sublist] +
                [str(v) for v in capability_ledger.values() if isinstance(v, str)]
            ).lower()
            
            for missing_concept in parsed["missing_concepts"]:
                if len(missing_concept) > 2 and missing_concept.lower() in flat_ledger:
                    parsed["ledger_contradiction_flag"] = True
                    logger.warning(
                        "Ledger contradiction flagged! LLM claims missing: '%s' but it exists in ledger.",
                        missing_concept
                    )
                    break

        parsed["verdict_bool"] = verdict_bool
        try:
            self._write_cache(cache_key, parsed)
        except Exception as exc:
            logger.warning("Failed to persist LLM cache entry: %s", exc)
        return parsed
