from uuid import UUID
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.clinician import Clinician

# Default clinician ID for local development
DEFAULT_CLINICIAN_ID = UUID("00000000-0000-0000-0000-000000000001")


async def get_or_create_default_clinician(db: AsyncSession) -> Clinician:
    """Get or create the default development clinician."""
    clinician = await db.get(Clinician, DEFAULT_CLINICIAN_ID)
    if not clinician:
        clinician = Clinician(
            id=DEFAULT_CLINICIAN_ID,
            email="dev@localhost",
            password_hash="not-used-in-dev",
            first_name="Development",
            last_name="Clinician",
            specialty="development",
        )
        db.add(clinician)
        await db.commit()
        await db.refresh(clinician)
    return clinician


async def get_current_clinician(db: AsyncSession = Depends(get_db)) -> Clinician:
    """
    Get current clinician - returns default clinician for local dev.
    Authentication will be added in Phase 6.
    """
    return await get_or_create_default_clinician(db)
