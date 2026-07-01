import re
import spacy
from typing import List
from app.schemas.capability import CapabilityObject, ObligationLevel
from app.knowledge.ontology import get_ontology

# Keyword fallback: maps common security terms to concept labels
# Used when spaCy model is unavailable
KEYWORD_FALLBACK = {
    "authentication": "Authentication",
    "mutual authentication": "Mutual Authentication",
    "password": "Password",
    "passwords": "Password",
    "rbac": "Role-Based Access Control",
    "role based access control": "Role-Based Access Control",
    "role-based access control": "Role-Based Access Control",
    "encryption": "Encryption",
    "tls": "TLS",
    "ssl": "SSL",
    "ssh": "SSH",
    "https": "HTTPS",
    "http": "HTTP",
    "ftp": "FTP",
    "telnet": "Telnet",
    "snmp": "SNMP",
    "certificate": "Digital Certificate",
    "x.509": "X.509 Certificate",
    "aes": "AES",
    "rsa": "RSA",
    "mfa": "Multi-Factor Authentication",
    "multi-factor": "Multi-Factor Authentication",
    "two-factor": "Multi-Factor Authentication",
    "session timeout": "Session Timeout",
    "inactivity": "Session Timeout",
    "audit": "Audit Logging",
    "logging": "Audit Logging",
    "log": "Audit Logging",
    "firewall": "Firewall",
    "vpn": "VPN",
    "ipsec": "IPsec",
    "integrity": "Data Integrity",
    "hashing": "Hashing",
    "hash": "Hashing",
    "digital signature": "Digital Signature",
    "signature": "Digital Signature",
    "ntp": "NTP",
    "time synchronization": "NTP",
    "bgp": "BGP",
    "routing": "Routing",
    "access control": "Access Control",
    "authorization": "Authorization",
    "privilege": "Privilege Management",
    "brute force": "Brute Force Protection",
    "lockout": "Account Lockout",
    "account lockout": "Account Lockout",
    "default password": "Default Credentials",
    "default credentials": "Default Credentials",
}


class CapabilityExtractor:
    """
    Extracts structured CapabilityObjects from requirement text using NLP (spaCy)
    and the Security Ontology. Falls back to keyword matching when spaCy unavailable.
    """
    def __init__(self):
        self.nlp = None
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            pass  # Will use keyword fallback

        self.ontology = get_ontology()

    def _extract_obligation(self, text: str) -> ObligationLevel:
        text_lower = text.lower()
        if "shall" in text_lower or "must" in text_lower:
            return ObligationLevel.SHALL
        elif "should" in text_lower:
            return ObligationLevel.SHOULD
        return ObligationLevel.MAY

    def _extract_version(self, context: str) -> str | None:
        context_lower = context.lower()
        if "v3" in context_lower or "version 3" in context_lower:
            return "v3"
        elif "v2" in context_lower or "version 2" in context_lower:
            return "v2"
        elif "1.3" in context_lower:
            return "1.3"
        elif "1.2" in context_lower:
            return "1.2"
        return None

    def extract(self, text: str) -> List[CapabilityObject]:
        obligation = self._extract_obligation(text)

        if self.nlp:
            return self._extract_spacy(text, obligation)
        else:
            return self._extract_keyword_fallback(text, obligation)

    def _extract_spacy(self, text: str, obligation: ObligationLevel) -> List[CapabilityObject]:
        doc = self.nlp(text)
        capabilities = []
        found_concepts = set()
        tokens = [token.text for token in doc]

        for n in range(3, 0, -1):
            for i in range(len(tokens) - n + 1):
                phrase = " ".join(tokens[i:i+n])
                resolved_id = self.ontology.resolve(phrase)
                if resolved_id and resolved_id not in found_concepts:
                    found_concepts.add(resolved_id)
                    start_idx = max(0, i - 2)
                    end_idx = min(len(tokens), i + n + 2)
                    context_phrase = " ".join(tokens[start_idx:end_idx])
                    version = self._extract_version(context_phrase)

                    capabilities.append(
                        CapabilityObject(
                            concept=self.ontology.graph.nodes[resolved_id].get("label", resolved_id),
                            version=version,
                            obligation=obligation,
                            source_text=phrase
                        )
                    )

        return capabilities

    def _extract_keyword_fallback(self, text: str, obligation: ObligationLevel) -> List[CapabilityObject]:
        """
        Keyword-based fallback when spaCy is unavailable.
        Scans for known security terms using multi-word match (longest match first).
        """
        text_lower = text.lower()
        capabilities = []
        found_spans = []  # track character spans to avoid duplicate overlapping matches

        # Sort by keyword length descending to prefer longer (more specific) matches
        sorted_keywords = sorted(KEYWORD_FALLBACK.keys(), key=len, reverse=True)

        for kw in sorted_keywords:
            for match in re.finditer(re.escape(kw), text_lower):
                span = (match.start(), match.end())
                # Check if this span overlaps with an already-found span
                overlaps = any(span[0] < s[1] and span[1] > s[0] for s in found_spans)
                if overlaps:
                    continue

                found_spans.append(span)
                concept_label = KEYWORD_FALLBACK[kw]
                # Extract surrounding context for version detection
                context = text[max(0, span[0]-15):min(len(text), span[1]+15)]
                version = self._extract_version(context)

                capabilities.append(
                    CapabilityObject(
                        concept=concept_label,
                        version=version,
                        obligation=obligation,
                        source_text=kw
                    )
                )

        return capabilities
