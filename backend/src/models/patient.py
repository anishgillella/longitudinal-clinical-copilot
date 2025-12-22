from sqlalchemy import String, Date, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4
from datetime import date
from typing import Optional, TYPE_CHECKING

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.clinician import Clinician
    from src.models.session import VoiceSession


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    clinician_id: Mapped[UUID] = mapped_column(ForeignKey("clinicians.id"), nullable=False)

    # Demographics
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Contact
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Clinical
    primary_concern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referral_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    intake_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")

    # Relationships
    clinician: Mapped["Clinician"] = relationship("Clinician", back_populates="patients")
    history: Mapped[list["PatientHistory"]] = relationship(
        "PatientHistory", back_populates="patient", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["VoiceSession"]] = relationship(
        "VoiceSession", back_populates="patient", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Patient {self.first_name} {self.last_name}>"


class PatientHistory(Base, TimestampMixin):
    __tablename__ = "patient_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)

    # History type
    history_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Source
    source: Mapped[str] = mapped_column(String(50), default="clinician_entry")
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Created by (optional for now, will link to clinician in future)
    created_by: Mapped[Optional[UUID]] = mapped_column(ForeignKey("clinicians.id"), nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="history")

    def __repr__(self) -> str:
        return f"<PatientHistory {self.title}>"
