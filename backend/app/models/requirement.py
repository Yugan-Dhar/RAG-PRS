from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, JSON, ForeignKey
from app.database import Base
import uuid

class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    framework_id: Mapped[str] = mapped_column(ForeignKey("frameworks.id"))
    req_id: Mapped[str] = mapped_column(String(100))
    parent_req_id: Mapped[str | None] = mapped_column(String(100))
    
    chapter: Mapped[str] = mapped_column(String(10)) # CSR or SSR
    section_number: Mapped[str | None] = mapped_column(String(20))
    section_title: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    
    obligation_level: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    
    # Applicability
    applicable_router_types: Mapped[list] = mapped_column(JSON, default=list)
    required_capability_flags: Mapped[list] = mapped_column(JSON, default=list)
    
    # Execution Logic Flags
    evidence_type: Mapped[str] = mapped_column(String(20), default="technical")
    is_prohibition: Mapped[bool] = mapped_column(default=False)
    is_table_row: Mapped[bool] = mapped_column(default=False)
    is_leaf: Mapped[bool] = mapped_column(default=True)
    compliance_by_undertaking: Mapped[bool] = mapped_column(default=False)
    
    # Pre-computed NLP fields
    expected_capabilities: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    cross_references: Mapped[list] = mapped_column(JSON, default=list)

    framework: Mapped["Framework"] = relationship(back_populates="requirements")
