from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.prescription import PrescriptionStatus


# ============ Prescription Item ============

class PrescriptionItemBase(BaseModel):
    product_id: int
    quantity_prescribed: int = Field(..., gt=0, description="Quantité prescrite")
    dosage: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    notes: Optional[str] = None


class PrescriptionItemCreate(PrescriptionItemBase):
    pass


class PrescriptionItem(PrescriptionItemBase):
    id: int
    prescription_id: int
    quantity_used: int
    created_at: datetime
    product: Optional["ProductSummary"] = None

    class Config:
        from_attributes = True


# ============ Prescription ============

class PrescriptionBase(BaseModel):
    customer_id: int
    doctor_name: str = Field(..., min_length=1, description="Nom du médecin")
    doctor_specialty: Optional[str] = None
    doctor_license_number: Optional[str] = None
    doctor_phone: Optional[str] = None
    prescription_date: datetime
    expiry_date: Optional[datetime] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    items: List[PrescriptionItemCreate] = Field(..., min_items=1, description="Produits prescrits")


class PrescriptionCreate(PrescriptionBase):
    pharmacy_id: int
    user_id: Optional[int] = None


class PrescriptionUpdate(BaseModel):
    doctor_name: Optional[str] = None
    doctor_specialty: Optional[str] = None
    doctor_license_number: Optional[str] = None
    doctor_phone: Optional[str] = None
    prescription_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[PrescriptionStatus] = None


class CustomerSummary(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True


class ProductSummary(BaseModel):
    id: int
    name: str
    barcode: Optional[str] = None
    sku: Optional[str] = None
    selling_price: float

    class Config:
        from_attributes = True


class Prescription(PrescriptionBase):
    id: int
    pharmacy_id: int
    user_id: Optional[int] = None
    prescription_number: str
    status: PrescriptionStatus
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None
    items: List[PrescriptionItem] = []
    customer: Optional[CustomerSummary] = None

    class Config:
        from_attributes = True


# Résoudre les références circulaires
PrescriptionItem.model_rebuild()
Prescription.model_rebuild()

