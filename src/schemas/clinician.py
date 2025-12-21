from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID
from typing import Optional


class ClinicianCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    license_number: Optional[str] = None
    specialty: Optional[str] = None


class ClinicianUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    license_number: Optional[str] = None
    specialty: Optional[str] = None
    is_active: Optional[bool] = None


class ClinicianResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    license_number: Optional[str]
    specialty: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
