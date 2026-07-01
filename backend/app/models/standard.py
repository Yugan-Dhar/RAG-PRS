from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, JSON, ForeignKey
from app.database import Base
import uuid

class Standard(Base):
    __tablename__ = "standards"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(String(50))
    frameworks: Mapped[list["Framework"]] = relationship(back_populates="standard")

class Framework(Base):
    __tablename__ = "frameworks"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    standard_id: Mapped[str] = mapped_column(ForeignKey("standards.id"))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    equipment_type: Mapped[str] = mapped_column(String(50))
    
    standard: Mapped["Standard"] = relationship(back_populates="frameworks")
    requirements: Mapped[list["Requirement"]] = relationship(back_populates="framework")
