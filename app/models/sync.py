from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncDirection(str, enum.Enum):
    UPLOAD = "upload"  # Local vers Cloud
    DOWNLOAD = "download"  # Cloud vers Local
    BIDIRECTIONAL = "bidirectional"


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Informations de synchronisation
    sync_id = Column(String, unique=True, nullable=False, index=True)  # ID unique de la session de sync
    direction = Column(Enum(SyncDirection), nullable=False)
    status = Column(Enum(SyncStatus), default=SyncStatus.PENDING, nullable=False)
    
    # Statistiques
    records_uploaded = Column(Integer, default=0, nullable=False)
    records_downloaded = Column(Integer, default=0, nullable=False)
    conflicts_count = Column(Integer, default=0, nullable=False)
    
    # Détails
    entity_type = Column(String, nullable=True)  # "product", "sale", etc.
    details = Column(JSON, nullable=True)  # Détails supplémentaires en JSON
    
    # Erreurs
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
