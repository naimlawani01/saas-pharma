from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class LicenseBase(BaseModel):
    license_key: str
    pharmacy_id: Optional[int] = None
    status: str = "active"
    max_activations: int = 2
    expires_at: Optional[datetime] = None
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    notes: Optional[str] = None


class LicenseCreate(LicenseBase):
    pass


class LicenseUpdate(BaseModel):
    status: Optional[str] = None
    max_activations: Optional[int] = None
    expires_at: Optional[datetime] = None
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    notes: Optional[str] = None


class LicenseActivationBase(BaseModel):
    hardware_id: str
    machine_name: Optional[str] = None
    os_info: Optional[str] = None


class LicenseActivationCreate(LicenseActivationBase):
    license_key: str


class LicenseActivationResponse(BaseModel):
    id: int
    license_id: int
    hardware_id: str
    machine_name: Optional[str]
    os_info: Optional[str]
    is_active: bool
    activation_token: str
    activated_at: datetime
    last_verified_at: Optional[datetime]
    deactivated_at: Optional[datetime]

    class Config:
        from_attributes = True


class LicenseResponse(BaseModel):
    id: int
    license_key: str
    pharmacy_id: Optional[int]
    status: str
    max_activations: int
    expires_at: Optional[datetime]
    customer_name: Optional[str]
    customer_email: Optional[str]
    customer_phone: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    activations: list[LicenseActivationResponse] = []

    class Config:
        from_attributes = True


class LicenseActivateRequest(BaseModel):
    license_key: str
    hardware_id: str
    machine_name: Optional[str] = None
    os_info: Optional[str] = None


class LicenseActivateResponse(BaseModel):
    success: bool
    message: str
    activation_token: Optional[str] = None
    license_id: Optional[int] = None


class LicenseVerifyRequest(BaseModel):
    hardware_id: str
    activation_token: Optional[str] = None


class LicenseVerifyResponse(BaseModel):
    valid: bool
    message: str
    license_status: Optional[str] = None
    expires_at: Optional[datetime] = None
    activations_count: Optional[int] = None
    max_activations: Optional[int] = None

