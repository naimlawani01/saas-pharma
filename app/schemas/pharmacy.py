from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class PharmacyBase(BaseModel):
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Guinée"
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None


class PharmacyCreate(PharmacyBase):
    pass


class PharmacyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    is_active: Optional[bool] = None


class Pharmacy(PharmacyBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None

    class Config:
        from_attributes = True
