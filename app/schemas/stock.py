from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.stock import (
    MovementType,
    AdjustmentReason,
    AlertType,
    AlertPriority,
)
from app.schemas.sale import ProductSummary


# ============ Stock Movement ============

class StockMovementBase(BaseModel):
    pharmacy_id: int
    product_id: int
    movement_type: MovementType
    quantity: int
    quantity_before: int
    quantity_after: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    unit_cost: Optional[float] = None
    notes: Optional[str] = None


class StockMovementCreate(StockMovementBase):
    user_id: int


class StockMovement(StockMovementBase):
    id: int
    user_id: int
    created_at: datetime
    product: Optional[ProductSummary] = None

    class Config:
        from_attributes = True


# ============ Stock Adjustment ============

class StockAdjustmentBase(BaseModel):
    pharmacy_id: int
    product_id: int
    quantity_adjusted: int  # Positif ou négatif
    reason: AdjustmentReason
    notes: Optional[str] = None


class StockAdjustmentCreate(StockAdjustmentBase):
    pass


class StockAdjustmentUpdate(BaseModel):
    notes: Optional[str] = None
    is_approved: Optional[bool] = None


class StockAdjustment(StockAdjustmentBase):
    id: int
    user_id: int
    quantity_before: int
    quantity_after: int
    is_approved: bool
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Alert ============

class AlertBase(BaseModel):
    pharmacy_id: int
    product_id: Optional[int] = None
    alert_type: AlertType
    priority: AlertPriority
    title: str
    message: str


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_resolved: Optional[bool] = None


class Alert(AlertBase):
    id: int
    is_read: bool
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Inventory ============

class InventoryItemBase(BaseModel):
    product_id: int
    quantity_counted: int
    notes: Optional[str] = None


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItem(InventoryItemBase):
    id: int
    inventory_id: int
    quantity_system: int
    quantity_difference: int

    class Config:
        from_attributes = True


class InventoryBase(BaseModel):
    pharmacy_id: int
    inventory_date: datetime
    notes: Optional[str] = None


class InventoryCreate(InventoryBase):
    items: List[InventoryItemCreate] = []


class InventoryUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class Inventory(InventoryBase):
    id: int
    user_id: int
    inventory_number: str
    status: str
    total_products_counted: int
    total_discrepancies: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[InventoryItem] = []

    class Config:
        from_attributes = True


# ============ Stats ============

class StockStats(BaseModel):
    """Statistiques de stock."""
    total_products: int
    low_stock_count: int
    out_of_stock_count: int
    expiring_soon_count: int
    expired_count: int
    total_value: float


class AlertStats(BaseModel):
    """Statistiques d'alertes."""
    total_alerts: int
    unread_count: int
    unresolved_count: int
    by_type: dict
    by_priority: dict

