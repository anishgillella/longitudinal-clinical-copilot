from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from uuid import UUID
from typing import Optional
from enum import Enum


class PatientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCHARGED = "discharged"


class HistoryType(str, Enum):
    MEDICAL = "medical"
    PSYCHIATRIC = "psychiatric"
    MEDICATION = "medication"
    LIFE_EVENT = "life_event"


# Patient schemas
class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    primary_concern: Optional[str] = None
    referral_source: Optional[str] = None


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    primary_concern: Optional[str] = None
    status: Optional[PatientStatus] = None


class PatientResponse(BaseModel):
    id: UUID
    clinician_id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    primary_concern: Optional[str]
    referral_source: Optional[str]
    intake_date: Optional[date]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    status: str
    intake_date: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True


# Patient History schemas
class PatientHistoryCreate(BaseModel):
    history_type: HistoryType
    title: str
    description: Optional[str] = None
    occurred_at: Optional[date] = None


class PatientHistoryResponse(BaseModel):
    id: UUID
    patient_id: UUID
    history_type: str
    title: str
    description: Optional[str]
    occurred_at: Optional[date]
    source: str
    confidence: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True
