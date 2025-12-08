from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False, index=True)
    
    # Informations client
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True, index=True)
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    
    # Informations médicales
    date_of_birth = Column(DateTime(timezone=True), nullable=True)
    allergies = Column(Text, nullable=True)
    medical_notes = Column(Text, nullable=True)
    
    # Statut
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="customers")
    sales = relationship("Sale", back_populates="customer")
    prescriptions = relationship("Prescription", back_populates="customer", cascade="all, delete-orphan")
    
    # Pour la synchronisation
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_id = Column(String, unique=True, nullable=True)
