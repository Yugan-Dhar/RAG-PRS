from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, JSON, ForeignKey
from app.database import Base
from datetime import datetime
import uuid

class AssessmentJob(Base):
    __tablename__ = "assessment_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    standard_id: Mapped[str] = mapped_column(String(50))
    framework_id: Mapped[str] = mapped_column(String(50))
    document_id: Mapped[str] = mapped_column(String(36))
    
    # ITSAR Specific
    router_type: Mapped[str | None] = mapped_column(String(50))
    capability_flags: Mapped[list] = mapped_column(JSON, default=list)
    
    status: Mapped[str] = mapped_column(String(20), default="queued")
    total_requirements: Mapped[int] = mapped_column(default=0)
    processed_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[str] = mapped_column(String(30), default=lambda: datetime.utcnow().isoformat())
    completed_at: Mapped[str | None] = mapped_column(String(30))
    
    results: Mapped[list["RequirementResult"]] = relationship(back_populates="job")

class RequirementResult(Base):
    __tablename__ = "requirement_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("assessment_jobs.id"))
    requirement_id: Mapped[str] = mapped_column(ForeignKey("requirements.id"))
    classification: Mapped[str] = mapped_column(String(20))    # Covered | Partial | Gap
    tier_reached: Mapped[int] = mapped_column(default=1)
    confidence: Mapped[dict] = mapped_column(JSON)
    reasoning: Mapped[str | None] = mapped_column(Text)
    gap_description: Mapped[str | None] = mapped_column(Text)
    expected_capabilities: Mapped[list] = mapped_column(JSON, default=list)
    observed_capabilities: Mapped[list] = mapped_column(JSON, default=list)
    missing_capabilities: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    evidence_quality: Mapped[dict | None] = mapped_column(JSON)
    
    # ITSAR Specific Execution Tracking
    is_undertaking_requirement: Mapped[bool] = mapped_column(default=False)
    undertaking_status: Mapped[str | None] = mapped_column(String(50))
    is_prohibition_requirement: Mapped[bool] = mapped_column(default=False)
    prohibition_violations: Mapped[list] = mapped_column(JSON, default=list)
    prohibition_compliant: Mapped[list] = mapped_column(JSON, default=list)
    
    # Roll-up fields
    is_leaf: Mapped[bool] = mapped_column(default=True)
    child_result_count: Mapped[int] = mapped_column(default=0)
    shall_gap_child_count: Mapped[int] = mapped_column(default=0)
    
    job: Mapped["AssessmentJob"] = relationship(back_populates="results")
