from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.models.sync import SyncStatus, SyncDirection


class SyncLogBase(BaseModel):
    direction: SyncDirection
    entity_type: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SyncLog(SyncLogBase):
    id: int
    pharmacy_id: int
    user_id: Optional[int] = None
    sync_id: str
    status: SyncStatus
    records_uploaded: int
    records_downloaded: int
    conflicts_count: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConflictResolution(BaseModel):
    entity_type: str  # "product", "sale", etc.
    entity_id: int
    local_version: Dict[str, Any]
    cloud_version: Dict[str, Any]
    resolution: str  # "local", "cloud", "merge"


class SyncRequest(BaseModel):
    direction: SyncDirection
    entity_types: Optional[List[str]] = None  # Si None, sync toutes les entités
    last_sync_at: Optional[datetime] = None
    conflicts: Optional[List[ConflictResolution]] = None


class SyncUploadPayload(BaseModel):
    entity_type: str  # "products", "sales", "customers", "suppliers", "orders"
    items: List[Dict[str, Any]]
    last_sync_at: Optional[datetime] = None


class SyncResponse(BaseModel):
    sync_id: str
    status: SyncStatus
    records_uploaded: int
    records_downloaded: int
    conflicts_count: int
    conflicts: Optional[List[ConflictResolution]] = None
    message: str
