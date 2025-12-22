from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from src.models.clinician import Clinician
from src.schemas.clinician import ClinicianCreate, ClinicianUpdate


class ClinicianService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[Clinician]:
        result = await self.db.execute(select(Clinician).order_by(Clinician.created_at.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, clinician_id: UUID) -> Optional[Clinician]:
        return await self.db.get(Clinician, clinician_id)

    async def get_by_email(self, email: str) -> Optional[Clinician]:
        result = await self.db.execute(select(Clinician).where(Clinician.email == email))
        return result.scalar_one_or_none()

    async def create(self, data: ClinicianCreate) -> Clinician:
        clinician = Clinician(
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            license_number=data.license_number,
            specialty=data.specialty,
        )
        self.db.add(clinician)
        await self.db.commit()
        await self.db.refresh(clinician)
        return clinician

    async def update(self, clinician_id: UUID, data: ClinicianUpdate) -> Optional[Clinician]:
        clinician = await self.get_by_id(clinician_id)
        if not clinician:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(clinician, field, value)

        await self.db.commit()
        await self.db.refresh(clinician)
        return clinician

    async def delete(self, clinician_id: UUID) -> bool:
        clinician = await self.get_by_id(clinician_id)
        if not clinician:
            return False

        await self.db.delete(clinician)
        await self.db.commit()
        return True
