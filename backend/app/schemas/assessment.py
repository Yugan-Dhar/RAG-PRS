from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class RequirementResultBase(BaseModel):
    requirement_id: str
    status: str
    confidence_score: float
    justification: Optional[str] = None
    evidence_references: List[str] = Field(default_factory=list)


class RequirementResultCreate(RequirementResultBase):
    pass


class RequirementResultRead(RequirementResultBase):
    id: str
    assessment_id: str

    class Config:
        from_attributes = True


class AssessmentJobBase(BaseModel):
    document_id: str
    standard_id: str
    framework_id: str


class AssessmentJobCreate(AssessmentJobBase):
    pass


class AssessmentJobRead(AssessmentJobBase):
    id: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class AssessmentResultCreate(BaseModel):
    requirement_id: str
    status: str
    confidence_score: float
    justification: str
    evidence_references: List[str] = Field(default_factory=list)
    analysis_details: Dict[str, Any] | None = None
