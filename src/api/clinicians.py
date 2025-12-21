from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.clinician import ClinicianCreate, ClinicianUpdate, ClinicianResponse
from src.services.clinician_service import ClinicianService

router = APIRouter(prefix="/clinicians", tags=["Clinicians"])


@router.get("", response_model=list[ClinicianResponse])
async def list_clinicians(db: AsyncSession = Depends(get_db)):
    """List all clinicians."""
    service = ClinicianService(db)
    clinicians = await service.get_all()
    return clinicians


@router.post("", response_model=ClinicianResponse, status_code=status.HTTP_201_CREATED)
async def create_clinician(data: ClinicianCreate, db: AsyncSession = Depends(get_db)):
    """Create a new clinician."""
    service = ClinicianService(db)

    # Check if email already exists
    existing = await service.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clinician with this email already exists",
        )

    clinician = await service.create(data)
    return clinician


@router.get("/{clinician_id}", response_model=ClinicianResponse)
async def get_clinician(clinician_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a clinician by ID."""
    service = ClinicianService(db)
    clinician = await service.get_by_id(clinician_id)
    if not clinician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinician not found",
        )
    return clinician


@router.put("/{clinician_id}", response_model=ClinicianResponse)
async def update_clinician(
    clinician_id: UUID,
    data: ClinicianUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a clinician."""
    service = ClinicianService(db)
    clinician = await service.update(clinician_id, data)
    if not clinician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinician not found",
        )
    return clinician


@router.delete("/{clinician_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clinician(clinician_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a clinician."""
    service = ClinicianService(db)
    deleted = await service.delete(clinician_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinician not found",
        )
