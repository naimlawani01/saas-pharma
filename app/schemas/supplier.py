from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.models.supplier import OrderStatus
from app.schemas.sale import ProductSummary


class SupplierBase(BaseModel):
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None


class SupplierCreate(SupplierBase):
    pharmacy_id: int


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    is_active: Optional[bool] = None


class Supplier(SupplierBase):
    id: int
    pharmacy_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SupplierOrderItemBase(BaseModel):
    product_id: int
    quantity_ordered: int
    unit_price: float


class SupplierOrderItemCreate(SupplierOrderItemBase):
    pass


class SupplierOrderItem(SupplierOrderItemBase):
    id: int
    order_id: int
    quantity_received: int
    total: float
    created_at: datetime
    product: Optional[ProductSummary] = None
    product_received_id: Optional[int] = None
    substitution_reason: Optional[str] = None
    is_returned: bool = False
    return_quantity: int = 0
    return_reason: Optional[str] = None
    return_date: Optional[datetime] = None
    received_at: Optional[datetime] = None
    product_received: Optional[ProductSummary] = None

    class Config:
        from_attributes = True


class SupplierOrderBase(BaseModel):
    supplier_id: int
    expected_delivery_date: Optional[datetime] = None
    subtotal: float = 0.0
    tax: float = 0.0
    shipping_cost: float = 0.0
    notes: Optional[str] = None
    items: List[SupplierOrderItemCreate]


class SupplierOrderCreate(SupplierOrderBase):
    pharmacy_id: int
    user_id: int


class SupplierOrderUpdate(BaseModel):
    expected_delivery_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    shipping_cost: Optional[float] = None
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None


class ReceiveItemRequest(BaseModel):
    """Schéma pour la réception d'un item individuel"""
    item_id: int
    quantity_received: int
    product_received_id: Optional[int] = None  # Si différent du produit commandé
    substitution_reason: Optional[str] = None  # Obligatoire si substitution
    notes: Optional[str] = None


class ReceiveOrderRequest(BaseModel):
    """Schéma pour la réception d'une commande ligne par ligne"""
    items: List[ReceiveItemRequest]


class ReturnItemRequest(BaseModel):
    """Schéma pour retourner un produit reçu"""
    item_id: int
    return_quantity: int
    return_reason: str  # Obligatoire


class SupplierOrder(SupplierOrderBase):
    id: int
    pharmacy_id: int
    user_id: int
    order_number: str
    order_date: datetime
    delivery_date: Optional[datetime] = None
    total_amount: float
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None
    items: List[SupplierOrderItem] = []
    supplier: Optional[SupplierBase] = None

    class Config:
        from_attributes = True
