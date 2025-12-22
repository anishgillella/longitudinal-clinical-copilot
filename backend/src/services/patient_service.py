from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional

from src.models.patient import Patient, PatientHistory
from src.schemas.patient import PatientCreate, PatientUpdate, PatientHistoryCreate


class PatientService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, clinician_id: Optional[UUID] = None) -> list[Patient]:
        query = select(Patient).order_by(Patient.created_at.desc())
        if clinician_id:
            query = query.where(Patient.clinician_id == clinician_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, patient_id: UUID) -> Optional[Patient]:
        return await self.db.get(Patient, patient_id)

    async def create(self, data: PatientCreate, clinician_id: UUID) -> Patient:
        patient = Patient(
            clinician_id=clinician_id,
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            email=data.email,
            phone=data.phone,
            primary_concern=data.primary_concern,
            referral_source=data.referral_source,
            intake_date=date.today(),
        )
        self.db.add(patient)
        await self.db.commit()
        await self.db.refresh(patient)
        return patient

    async def update(self, patient_id: UUID, data: PatientUpdate) -> Optional[Patient]:
        patient = await self.get_by_id(patient_id)
        if not patient:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(patient, field, value)

        await self.db.commit()
        await self.db.refresh(patient)
        return patient

    async def delete(self, patient_id: UUID) -> bool:
        """Soft delete - set status to discharged."""
        patient = await self.get_by_id(patient_id)
        if not patient:
            return False

        patient.status = "discharged"
        await self.db.commit()
        return True

    # Patient History methods
    async def get_history(
        self, patient_id: UUID, history_type: Optional[str] = None
    ) -> list[PatientHistory]:
        query = select(PatientHistory).where(PatientHistory.patient_id == patient_id)
        if history_type:
            query = query.where(PatientHistory.history_type == history_type)
        query = query.order_by(PatientHistory.occurred_at.desc().nullslast())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def add_history(
        self, patient_id: UUID, data: PatientHistoryCreate, clinician_id: Optional[UUID] = None
    ) -> PatientHistory:
        history = PatientHistory(
            patient_id=patient_id,
            history_type=data.history_type.value,
            title=data.title,
            description=data.description,
            occurred_at=data.occurred_at,
            source="clinician_entry",
            created_by=clinician_id,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def get_history_by_id(self, history_id: UUID) -> Optional[PatientHistory]:
        return await self.db.get(PatientHistory, history_id)

    async def delete_history(self, history_id: UUID) -> bool:
        history = await self.get_history_by_id(history_id)
        if not history:
            return False

        await self.db.delete(history)
        await self.db.commit()
        return True
