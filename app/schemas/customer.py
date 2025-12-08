from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class CustomerBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    allergies: Optional[str] = None
    medical_notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    pharmacy_id: int


class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    allergies: Optional[str] = None
    medical_notes: Optional[str] = None
    is_active: Optional[bool] = None


class Customer(CustomerBase):
    id: int
    pharmacy_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None

    class Config:
        from_attributes = True
