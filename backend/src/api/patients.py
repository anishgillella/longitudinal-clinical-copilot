from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.clinician import Clinician
from src.api.deps import get_current_clinician
from src.schemas.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    PatientListResponse,
    PatientHistoryCreate,
    PatientHistoryResponse,
    HistoryType,
)
from src.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("", response_model=list[PatientListResponse])
async def list_patients(
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """List all patients for the current clinician."""
    service = PatientService(db)
    patients = await service.get_all(clinician_id=clinician.id)

    if status:
        patients = [p for p in patients if p.status == status]

    return patients


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    data: PatientCreate,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Create a new patient."""
    service = PatientService(db)
    patient = await service.create(data, clinician_id=clinician.id)
    return patient


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Get a patient by ID."""
    service = PatientService(db)
    patient = await service.get_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    # Check ownership
    if patient.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this patient",
        )
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Update a patient."""
    service = PatientService(db)

    # Check ownership first
    patient = await service.get_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    if patient.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this patient",
        )

    updated = await service.update(patient_id, data)
    return updated


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Soft delete a patient (set status to discharged)."""
    service = PatientService(db)

    # Check ownership first
    patient = await service.get_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    if patient.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this patient",
        )

    await service.delete(patient_id)


# Patient History endpoints
@router.get("/{patient_id}/history", response_model=list[PatientHistoryResponse])
async def get_patient_history(
    patient_id: UUID,
    history_type: Optional[HistoryType] = Query(None, description="Filter by history type"),
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Get patient history."""
    service = PatientService(db)

    # Check patient exists and ownership
    patient = await service.get_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    if patient.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this patient",
        )

    history_type_str = history_type.value if history_type else None
    history = await service.get_history(patient_id, history_type=history_type_str)
    return history


@router.post(
    "/{patient_id}/history",
    response_model=PatientHistoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_patient_history(
    patient_id: UUID,
    data: PatientHistoryCreate,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Add a history entry for a patient."""
    service = PatientService(db)

    # Check patient exists and ownership
    patient = await service.get_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    if patient.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add history for this patient",
        )

    history = await service.add_history(patient_id, data, clinician_id=clinician.id)
    return history


@router.delete("/{patient_id}/history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient_history(
    patient_id: UUID,
    history_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Delete a patient history entry."""
    service = PatientService(db)

    # Check patient exists and ownership
    patient = await service.get_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    if patient.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete history for this patient",
        )

    deleted = await service.delete_history(history_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History entry not found",
        )
