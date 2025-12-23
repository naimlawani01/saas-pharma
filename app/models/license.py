from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class License(Base):
    """
    Modèle pour les licences d'utilisation de l'application.
    """
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String, unique=True, nullable=False, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=True)
    
    # Informations sur la licence
    status = Column(String, default="active", nullable=False)  # active, expired, revoked, suspended
    max_activations = Column(Integer, default=2, nullable=False)  # Nombre maximum de machines autorisées
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Date d'expiration (null = perpétuelle)
    
    # Informations client
    customer_name = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    
    # Notes internes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="license")
    activations = relationship("LicenseActivation", back_populates="license", cascade="all, delete-orphan")


class LicenseActivation(Base):
    """
    Modèle pour les activations de licence sur différentes machines.
    """
    __tablename__ = "license_activations"

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=False, index=True)
    
    # Identifiant unique de la machine
    hardware_id = Column(String, nullable=False, index=True)
    
    # Informations sur la machine
    machine_name = Column(String, nullable=True)
    os_info = Column(String, nullable=True)  # OS, version, etc.
    
    # Statut de l'activation
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Token d'activation (chiffré)
    activation_token = Column(String, nullable=False, unique=True, index=True)
    
    # Timestamps
    activated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    license = relationship("License", back_populates="activations")

