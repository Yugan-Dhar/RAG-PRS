from typing import List, Dict, Any
import logging
import asyncio
import json
import hashlib
import os
from pathlib import Path
import urllib3
from dotenv import load_dotenv
import socket

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Override DNS resolution for api.cerebras.ai to bypass local corporate DNS/VPN issues
# while preserving the proper hostname for Host header and SNI
_original_getaddrinfo = socket.getaddrinfo
def _custom_getaddrinfo(*args, **kwargs):
    if args and args[0] == 'api.cerebras.ai':
        # Return Cloudflare's IP address for Cerebras
        port = args[1] if len(args) > 1 else 443
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('104.18.11.146', port))]
    return _original_getaddrinfo(*args, **kwargs)
socket.getaddrinfo = _custom_getaddrinfo

logger = logging.getLogger(__name__)

GROQ_SEMAPHORE = None
OLLAMA_LOCK = None


class Tier3LLM:
    """
    Uses a local Ollama model to produce structured gap-analysis output.
    The orchestrator treats this as one signal among several, not the sole judge.
    """

    CACHE_VERSION = "v7"

    def __init__(
        self,
        host: str = "http://127.0.0.1:11434",
        model: str = "llama3.2:latest",
        cache_dir: str | None = None,
    ):
        self.host = host
        if os.environ.get("CEREBRAS_API_KEY"):
            self.model = "gpt-oss-120b"
        elif os.environ.get("GROQ_API_KEY"):
            self.model = "llama-3.1-8b-instant"
        else:
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

    def _call_llm_sync(self, prompt: str) -> str:
        """Synchronous network call to LLM, intended to be wrapped in run_in_executor"""
        import time
        import re
        max_retries = 15
        
        cerebras_api_key = os.environ.get("CEREBRAS_API_KEY")
        groq_api_key = os.environ.get("GROQ_API_KEY")
        
        if cerebras_api_key:
            # Use Cerebras (Free 70B, blazing fast)
            url = "https://api.cerebras.ai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {cerebras_api_key}",
                "Content-Type": "application/json"
            }
            json_payload = {
                "model": "gpt-oss-120b",
                "messages": [
                    {"role": "system", "content": "You are a stringent cybersecurity auditor."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0
            }
        elif groq_api_key:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            }
            json_payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are a stringent cybersecurity auditor."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0
            }
        else:
            url = "http://localhost:11434/api/chat"
            headers = {"Content-Type": "application/json"}
            json_payload = {
                "model": "phi3.5:mini",
                "messages": [
                    {"role": "system", "content": "You are a stringent cybersecurity auditor."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.0,
                    "num_ctx": 4096
                }
            }

        for attempt in range(max_retries):
            try:
                response = self.requests.post(
                    url,
                    headers=headers,
                    json=json_payload,
                    timeout=60,
                    verify=False
                )
                if response.status_code == 429:
                    sleep_time = float(response.headers.get("retry-after", 0.0))
                    msg = ""
                    if sleep_time == 0.0:
                        try:
                            error_json = response.json()
                            msg = error_json.get("error", {}).get("message", "")
                            # Match formats like "try again in 7m12s" or "try again in 4.5s"
                            match = re.search(r"try again in (?:(\d+)m)?(\d+\.?\d*)s", msg)
                            if match:
                                minutes = float(match.group(1)) if match.group(1) else 0.0
                                seconds = float(match.group(2))
                                sleep_time = minutes * 60 + seconds
                            else:
                                sleep_time = 10.0
                        except Exception:
                            sleep_time = 10.0
                            
                    print(f"API rate limit hit (429). Requested sleep: {sleep_time} seconds. Msg: {msg}")
                    logger.warning(f"API rate limit hit (429). Sleeping for {sleep_time} seconds before retry.")
                    
                    if sleep_time > 120:
                        print(f"Sleep time {sleep_time}s is too long. Failing fast.")
                        raise Exception(f"API Rate Limit exceeded. Requires {sleep_time}s cooldown.")
                        
                    time.sleep(sleep_time)
                    continue
                
                response.raise_for_status()
                
                if cerebras_api_key or groq_api_key:
                    return response.json()["choices"][0]["message"]["content"].strip()
                else:
                    return response.json().get("message", {}).get("content", "").strip()
            except Exception as e:
                # If we get connection errors, wait and retry
                print(f"Network error in LLM call: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(5.0)
                continue
                
        raise Exception("API rate limit exceeded after maximum retries.")

    def _build_gap_analysis_prompt(
        self,
        requirement_title: str,
        requirement_text: str,
        evidence_chunks: List[Dict[str, Any]],
        capability_ledger: Dict[str, Any] = None,
        expected_capabilities: List[str] = None
    ) -> str:
        context_parts = []
        for i, chunk in enumerate(evidence_chunks[:8]):
            text = chunk.get("payload", {}).get("text", "").strip()
            chunk_id = chunk.get("id", f"excerpt-{i + 1}")
            if text:
                context_parts.append(f"[{chunk_id}] {text[:2000]}")
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
            "- COMPLIANT: The evidence demonstrates the intent and capability required by the requirement. "
            "Evidence does NOT need to use the exact same words as the standard — if the documented features "
            "functionally satisfy the requirement through equivalent mechanisms, this is COMPLIANT. "
            "Minor phrasing differences or implicit capabilities that logically follow from the evidence are acceptable.\n"
            "- PARTIAL: The evidence covers some sub-clauses but key capabilities are genuinely missing, "
            "contradicted, or the evidence only addresses a subset of what is required. List the specific gaps.\n"
            "- NON-COMPLIANT: The evidence contradicts the requirement, or no relevant evidence exists for ANY sub-clause.\n\n"
            "CRITICAL RULES:\n"
            "- If the requirement mentions an OEM undertaking or self-declaration, treat that as a procedural/administrative "
            "artifact to be verified separately. Focus your assessment on the product-testable technical parts. "
            "Do NOT mark as PARTIAL solely because an undertaking document is not present in the excerpts.\n"
            "- Break the requirement into individual sub-clauses and evaluate each one.\n"
            "- Use COMPLIANT when the evidence functionally addresses the requirement, even if not verbatim.\n"
            "- Use PARTIAL only for genuine, material gaps — not for minor phrasing differences.\n"
            "- Use NON-COMPLIANT only when the evidence clearly contradicts or is completely silent.\n\n"
            "GUIDELINES FOR JUSTIFICATION:\n"
            "- Write a concise explanation in 2-3 natural sentences.\n"
            "- Start by describing what the requirement expects.\n"
            "- Summarize the capabilities supported by the evidence, including reasonable inferences.\n"
            "- Identify any required capability genuinely not demonstrated.\n"
            "- Avoid generic phrases ('analysis indicates', 'the product is compliant').\n"
            "- Do not repeat the verdict or confidence score.\n"
            "- Vary your sentence structure naturally depending on the evidence.\n\n"
            "Return exactly one valid JSON object with these keys:\n"
            "{\n"
            '  "concept_analysis": [\n'
            '    {"concept": "mandatory concept from requirement", "status": "evidenced, absent, or uncertain", "excerpt": "relevant evidence snippet if found"}\n'
            '  ],\n'
            '  "verdict": "COMPLIANT" or "PARTIAL" or "NON-COMPLIANT",\n'
            '  "gaps": ["specific sub-clause or capability that genuinely lacks evidence"],\n'
            '  "extracted_evidence": ["short direct evidence statements copied or paraphrased from excerpts"],\n'
            '  "matched_concepts": ["requirement concepts that are evidenced or functionally satisfied"],\n'
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
            global GROQ_SEMAPHORE, OLLAMA_LOCK
            cerebras_active = bool(os.environ.get("CEREBRAS_API_KEY"))
            groq_active = bool(os.environ.get("GROQ_API_KEY"))
            
            if cerebras_active or groq_active:
                # Cerebras and Groq have generous RPM but strict TPM on free tiers.
                # Semaphore(3) helps smooth out sudden bursts.
                if GROQ_SEMAPHORE is None:
                    GROQ_SEMAPHORE = asyncio.Semaphore(3)
                limiter = GROQ_SEMAPHORE
            else:
                # Local Ollama: serialize requests to avoid CPU contention
                if OLLAMA_LOCK is None:
                    OLLAMA_LOCK = asyncio.Lock()
                limiter = OLLAMA_LOCK
                
            loop = asyncio.get_event_loop()
            async with limiter:
                # We pass the prompt, and determine which API to call inside _call_llm_sync
                answer = await loop.run_in_executor(None, self._call_llm_sync, prompt)
                
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
        
        if verdict != "ANALYSIS_FAILED":
            try:
                self._write_cache(cache_key, parsed)
            except Exception as exc:
                logger.warning("Failed to persist LLM cache entry: %s", exc)
                
        return parsed
