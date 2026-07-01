from pydantic import BaseModel, Field
from enum import Enum

class ObligationLevel(str, Enum):
    SHALL = "SHALL"
    SHOULD = "SHOULD"
    MAY = "MAY"

class CapabilityObject(BaseModel):
    concept: str
    protocol: str | None = None
    version: str | None = None
    operation: str | None = None
    scope: str | None = None
    strength: str | None = None
    obligation: ObligationLevel = ObligationLevel.SHALL
    source_text: str | None = None
    
    def matches(self, other: "CapabilityObject", ontology) -> float:
        if self.concept.lower() == other.concept.lower():
            concept_score = 1.0
        elif ontology.are_related(self.concept, other.concept):
            concept_score = 0.6
        else:
            return 0.0
        
        protocol_score = 1.0
        if self.protocol:
            if other.protocol and self.protocol.lower() == other.protocol.lower():
                protocol_score = 1.0
            elif other.protocol:
                protocol_score = 0.3
            else:
                protocol_score = 0.5
        
        version_score = 1.0
        if self.version:
            if other.version and self.version == other.version:
                version_score = 1.0
            elif other.version:
                version_score = 0.1
            else:
                version_score = 0.4
        
        return concept_score * 0.5 + protocol_score * 0.3 + version_score * 0.2

class EvidenceQuality(BaseModel):
    completeness: float = Field(ge=0.0, le=1.0)
    specificity: float = Field(ge=0.0, le=1.0)
    currency: float = Field(ge=0.0, le=1.0)
    directness: float = Field(ge=0.0, le=1.0)
    
    @property
    def score(self) -> float:
        return (self.completeness + self.specificity + self.currency + self.directness) / 4.0

class ConfidenceScores(BaseModel):
    semantic: float = Field(ge=0.0, le=1.0)
    capability: float = Field(ge=0.0, le=1.0)
    evidence_quality: float = Field(ge=0.0, le=1.0)
    reasoning: float = Field(ge=0.0, le=1.0, default=0.0)
    
    @property
    def overall(self) -> float:
        return (
            0.25 * self.semantic +
            0.35 * self.capability +
            0.25 * self.evidence_quality +
            0.15 * self.reasoning
        )

class CoverageClass(str, Enum):
    COVERED = "Covered"
    PARTIAL = "Partial"
    GAP = "Gap"
    BORDERLINE = "Borderline"
