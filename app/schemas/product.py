from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.product import ProductUnit


class ProductCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProductCategoryCreate(ProductCategoryBase):
    pass


class ProductCategory(ProductCategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    barcode: Optional[str] = None
    sku: Optional[str] = None
    category_id: Optional[int] = None
    quantity: int = 0
    min_quantity: int = 0
    unit: ProductUnit = ProductUnit.UNIT
    purchase_price: float
    selling_price: float
    expiry_date: Optional[datetime] = None
    manufacturing_date: Optional[datetime] = None
    is_prescription_required: bool = False
    
    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v):
        if v < 0:
            raise ValueError("La quantité ne peut pas être négative")
        return v
    
    @field_validator("min_quantity")
    @classmethod
    def validate_min_quantity(cls, v):
        if v < 0:
            raise ValueError("La quantité minimale ne peut pas être négative")
        return v
    
    @field_validator("purchase_price")
    @classmethod
    def validate_purchase_price(cls, v):
        if v < 0:
            raise ValueError("Le prix d'achat ne peut pas être négatif")
        return v
    
    @field_validator("selling_price")
    @classmethod
    def validate_selling_price(cls, v):
        if v < 0:
            raise ValueError("Le prix de vente ne peut pas être négatif")
        return v


class ProductCreate(ProductBase):
    pharmacy_id: int


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    barcode: Optional[str] = None
    sku: Optional[str] = None
    category_id: Optional[int] = None
    quantity: Optional[int] = None
    min_quantity: Optional[int] = None
    unit: Optional[ProductUnit] = None
    purchase_price: Optional[float] = None
    selling_price: Optional[float] = None
    expiry_date: Optional[datetime] = None
    manufacturing_date: Optional[datetime] = None
    is_prescription_required: Optional[bool] = None
    is_active: Optional[bool] = None


class Product(ProductBase):
    id: int
    pharmacy_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None
    category: Optional[ProductCategory] = None

    class Config:
        from_attributes = True
