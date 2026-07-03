from typing import Dict, Any, List
import logging
import asyncio
import json

from app.analysis.tier3_llm import Tier3LLM
from app.retrieval.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)

class CapabilityExtractor:
    def __init__(self, retriever: HybridRetriever, llm: Tier3LLM = None):
        self.retriever = retriever
        self.llm = llm or Tier3LLM()

    def _build_ledger_prompt(self, evidence_chunks: List[Dict[str, Any]]) -> str:
        evidence_text = ""
        for i, chunk in enumerate(evidence_chunks):
            text = chunk.get("payload", {}).get("text", "")
            if text:
                evidence_text += f"\n[Chunk {i+1}]\n{text}\n"

        return f"""You are a cybersecurity auditor extracting canonical product facts from documentation.
Analyze the following excerpts and build a definitive ledger of supported capabilities.
ONLY include capabilities that are EXPLICITLY stated as supported by the product.
If the excerpts do not explicitly state a capability, leave the value as `null` or an empty list `[]`. Do NOT guess.

Excerpts:
{evidence_text}

Output ONLY valid JSON matching this schema:
{{
  "authentication_methods": ["list of supported auth methods, e.g., RADIUS, TACACS+, Local, etc. or []"],
  "cryptographic_protocols": ["list of supported crypto protocols, e.g., TLSv1.2, SSHv2, IPsec, etc. or []"],
  "management_interfaces": ["list of supported interfaces, e.g., CLI, Web GUI, SNMP, NETCONF, etc. or []"],
  "default_session_timeout": "string describing default timeout if found, else null",
  "default_lockout_policy": "string describing lockout threshold/duration if found, else null"
}}

Respond with the JSON object only. Do not include markdown or extra text.
"""

    async def build_ledger(self, doc_id: str = None) -> Dict[str, Any]:
        logger.info("Building Capability Ledger...")
        
        # We run 4 targeted queries to gather global facts
        queries = [
            ("authentication protocols RADIUS TACACS+ local auth", "authentication protocols"),
            ("cryptographic protocols algorithms TLS SSH IPsec AES", "cryptographic protocols TLS SSH"),
            ("management interfaces GUI CLI SNMP NETCONF", "management interfaces"),
            ("password policy session timeout account lockout", "session timeout account lockout")
        ]
        
        all_chunks = []
        for dense_q, sparse_q in queries:
            chunks = self.retriever.retrieve(dense_query=dense_q, sparse_query=sparse_q, top_k=3)
            all_chunks.extend(chunks)
            
        # Deduplicate by ID
        unique_chunks_dict = {str(chunk.get("id")): chunk for chunk in all_chunks}
        unique_chunks = list(unique_chunks_dict.values())[:10] # Cap to top 10 diverse chunks
        
        prompt = self._build_ledger_prompt(unique_chunks)
        
        loop = asyncio.get_running_loop()
        try:
            from app.analysis.tier3_llm import OLLAMA_LOCK
            if OLLAMA_LOCK:
                async with OLLAMA_LOCK:
                    response_text = await loop.run_in_executor(None, self.llm._call_ollama_sync, prompt)
            else:
                response_text = await loop.run_in_executor(None, self.llm._call_ollama_sync, prompt)
                
            ledger = json.loads(response_text)
            logger.info("Capability Ledger built successfully: %s", json.dumps(ledger))
            return ledger
        except Exception as e:
            logger.error("Failed to build capability ledger: %s", e)
            # Return empty/safe ledger on failure to avoid poisoning
            return {
                "authentication_methods": [],
                "cryptographic_protocols": [],
                "management_interfaces": [],
                "default_session_timeout": None,
                "default_lockout_policy": None
            }
