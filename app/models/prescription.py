from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class PrescriptionStatus(str, enum.Enum):
    ACTIVE = "active"  # Prescription active, peut être utilisée
    USED = "used"  # Prescription utilisée (tous les produits vendus)
    PARTIALLY_USED = "partially_used"  # Prescription partiellement utilisée
    EXPIRED = "expired"  # Prescription expirée
    CANCELLED = "cancelled"  # Prescription annulée


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Utilisateur qui a enregistré la prescription
    
    # Numéro de prescription (unique par pharmacie)
    prescription_number = Column(String, nullable=False, index=True)
    
    # Informations du médecin
    doctor_name = Column(String, nullable=False)
    doctor_specialty = Column(String, nullable=True)
    doctor_license_number = Column(String, nullable=True)  # RPPS, ADELI, etc.
    doctor_phone = Column(String, nullable=True)
    
    # Dates
    prescription_date = Column(DateTime(timezone=True), nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=True)  # Date d'expiration de la prescription
    
    # Statut
    status = Column(Enum(PrescriptionStatus), default=PrescriptionStatus.ACTIVE, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)  # Diagnostic ou motif
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="prescriptions")
    customer = relationship("Customer", back_populates="prescriptions")
    user = relationship("User")
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="prescription")
    
    # Pour la synchronisation
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_id = Column(String, unique=True, nullable=True)


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Quantité prescrite
    quantity_prescribed = Column(Integer, nullable=False)
    
    # Quantité déjà vendue (pour suivre l'utilisation)
    quantity_used = Column(Integer, default=0, nullable=False)
    
    # Instructions de prise
    dosage = Column(String, nullable=True)  # Ex: "1 comprimé matin et soir"
    duration = Column(String, nullable=True)  # Ex: "7 jours"
    instructions = Column(Text, nullable=True)  # Instructions détaillées
    
    # Notes spécifiques au produit
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relations
    prescription = relationship("Prescription", back_populates="items")
    product = relationship("Product")

