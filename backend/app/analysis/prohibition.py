import re
from typing import List, Dict, Any, Tuple

# ── Negation patterns ────────────────────────────────────────────────────────
# If any of these appear near a prohibited keyword, the product is explicitly
# stating the service is REMOVED / DISABLED → prohibition requirement SATISFIED.
NEGATION_CONTEXTS = [
    "excluded", "exclude", "exclusion",
    "not supported", "not support",
    "disabled", "disable",
    "removed", "removal", "remove",
    "not allowed", "prohibited",
    "deactivated", "deactivate",
    "not permitted",
    "not included",
    "not available",
    "rejected",
    "blocked",
    "not enabled",
    "not used",
    "not utilized",
    "is not",
    "does not support",
    "cannot",
    "must not",
    "shall not",
    "will not",
    "no support",
    "not provide",
    "not offered",
]

# ── Section-level exclusion headings ─────────────────────────────────────────
# If a chunk's text contains any of these as a heading / section title,
# ALL keyword mentions in that chunk are treated as exclusion signals (compliant).
EXCLUSION_SECTION_HEADERS = [
    "excluded functionality",
    "not supported functionality",
    "excluded from evaluation",
    "disabled by default",
    "functionality not provided",
    "services not supported",
    "unsupported features",
    "features not supported",
    "protocols not supported",
    "excluded features",
    "security functions excluded",
    "non-tsf services",
    "non-security functionality excluded",
]


class ProhibitionAnalyser:
    """
    Context-aware prohibition analyser.

    Naive keyword matching causes false positives when a prohibited service
    is mentioned in an "Excluded Functionality" table (meaning it is explicitly
    NOT supported). This analyser checks:

    1. **Chunk-level exclusion header**: if the entire chunk contains an
       exclusion heading (e.g. "Excluded Functionality"), all keyword
       occurrences in that chunk are treated as compliance signals.

    2. **Context window negation**: a ±300-char window around each keyword
       occurrence is checked for negation phrases.

    A keyword is a VIOLATION only when it appears WITHOUT any surrounding
    negation/exclusion context.

    Examples:
    - "Excluded Functionality: FTP – non-FIPS mode"  → COMPLIANT
    - "FTP is excluded from evaluation"               → COMPLIANT
    - "The router supports FTP for configuration"     → NON-COMPLIANT
    """

    CONTEXT_WINDOW = 300  # characters either side of a keyword occurrence

    def _chunk_is_exclusion_section(self, chunk_text: str) -> bool:
        """Return True if the chunk comes from an exclusion / not-supported section."""
        lower = chunk_text.lower()
        return any(header in lower for header in EXCLUSION_SECTION_HEADERS)

    def _find_keyword_contexts(self, text: str, keyword: str) -> List[str]:
        """Return a list of context windows around each occurrence of keyword."""
        text_lower = text.lower()
        kw_lower = keyword.lower()
        contexts = []
        start = 0
        while True:
            idx = text_lower.find(kw_lower, start)
            if idx == -1:
                break
            w_start = max(0, idx - self.CONTEXT_WINDOW)
            w_end = min(len(text_lower), idx + len(kw_lower) + self.CONTEXT_WINDOW)
            contexts.append(text_lower[w_start:w_end])
            start = idx + 1
        return contexts

    def _is_negated_occurrence(self, context: str) -> bool:
        """Return True if the context window contains a negation phrase."""
        for neg in NEGATION_CONTEXTS:
            if neg in context:
                return True
        return False

    def analyze(
        self,
        keywords: List[str],
        evidence_chunks: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Returns (is_compliant, violations).

        A keyword is a VIOLATION only when it appears in evidence without
        any surrounding negation/exclusion context AND the chunk is not an
        exclusion-section chunk.
        """
        violations: List[str] = []

        for kw in keywords:
            if not kw.strip():
                continue

            kw_violated = False
            for chunk in evidence_chunks:
                chunk_text = chunk["payload"].get("text", "")

                # ── Chunk-level exclusion header check ───────────────────────
                if self._chunk_is_exclusion_section(chunk_text):
                    # The whole chunk is an "Excluded Functionality" section.
                    # Finding the keyword here is a compliance SIGNAL, not a violation.
                    continue

                # ── Context-window negation check ─────────────────────────────
                contexts = self._find_keyword_contexts(chunk_text, kw)
                non_negated = [ctx for ctx in contexts if not self._is_negated_occurrence(ctx)]
                if non_negated:
                    kw_violated = True
                    break  # one confirmed violation is enough

            if kw_violated:
                violations.append(kw)

        is_compliant = len(violations) == 0
        return is_compliant, violations
