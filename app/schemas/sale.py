from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.sale import PaymentMethod, SaleStatus


class ProductSummary(BaseModel):
    """Résumé du produit pour affichage dans les items de vente"""
    id: int
    name: str
    barcode: Optional[str] = None
    selling_price: float

    class Config:
        from_attributes = True


class SaleItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    discount: float = 0.0
    
    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("La quantité doit être supérieure à 0")
        return v
    
    @field_validator("unit_price")
    @classmethod
    def validate_unit_price(cls, v):
        if v < 0:
            raise ValueError("Le prix unitaire ne peut pas être négatif")
        return v
    
    @field_validator("discount")
    @classmethod
    def validate_discount(cls, v):
        if v < 0:
            raise ValueError("La remise ne peut pas être négative")
        return v


class SaleItemCreate(SaleItemBase):
    pass


class SaleItem(SaleItemBase):
    id: int
    sale_id: int
    total: float
    created_at: datetime
    product: Optional[ProductSummary] = None

    class Config:
        from_attributes = True


class SaleBase(BaseModel):
    customer_id: Optional[int] = None
    prescription_id: Optional[int] = None
    total_amount: float
    discount: float = 0.0
    tax: float = 0.0
    payment_method: PaymentMethod = PaymentMethod.CASH
    notes: Optional[str] = None
    items: List[SaleItemCreate]
    
    @field_validator("total_amount")
    @classmethod
    def validate_total_amount(cls, v):
        if v < 0:
            raise ValueError("Le montant total ne peut pas être négatif")
        return v
    
    @field_validator("discount")
    @classmethod
    def validate_discount(cls, v):
        if v < 0:
            raise ValueError("La remise ne peut pas être négative")
        return v
    
    @field_validator("tax")
    @classmethod
    def validate_tax(cls, v):
        if v < 0:
            raise ValueError("La taxe ne peut pas être négative")
        return v
    
    @field_validator("items")
    @classmethod
    def validate_items(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Une vente doit contenir au moins un article")
        return v


class SaleCreate(SaleBase):
    pharmacy_id: int
    user_id: int


class SaleUpdate(BaseModel):
    customer_id: Optional[int] = None
    prescription_id: Optional[int] = None
    discount: Optional[float] = None
    tax: Optional[float] = None
    payment_method: Optional[PaymentMethod] = None
    status: Optional[SaleStatus] = None
    notes: Optional[str] = None


class Sale(SaleBase):
    id: int
    pharmacy_id: int
    user_id: int
    prescription_id: Optional[int] = None
    sale_number: str
    final_amount: float
    status: SaleStatus
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None
    items: List[SaleItem] = []

    class Config:
        from_attributes = True
