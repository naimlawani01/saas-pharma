from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Pharmacy(Base):
    """
    Modèle pour les commerces/entreprises.
    Note: Le nom 'pharmacies' est conservé pour compatibilité avec les migrations existantes,
    mais ce modèle représente tout type de commerce (pharmacie, épicerie, quincaillerie, etc.)
    """
    __tablename__ = "pharmacies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, default="Guinée", nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    license_number = Column(String, unique=True, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Type d'activité : pharmacy, grocery, hardware, cosmetics, auto_parts, clothing, electronics, restaurant, wholesale, general
    business_type = Column(String, default="general", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    users = relationship("User", back_populates="pharmacy")
    products = relationship("Product", back_populates="pharmacy", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="pharmacy", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="pharmacy", cascade="all, delete-orphan")
    suppliers = relationship("Supplier", back_populates="pharmacy", cascade="all, delete-orphan")
    stock_movements = relationship("StockMovement", back_populates="pharmacy", cascade="all, delete-orphan")
    stock_adjustments = relationship("StockAdjustment", back_populates="pharmacy", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="pharmacy", cascade="all, delete-orphan")
    inventories = relationship("Inventory", back_populates="pharmacy", cascade="all, delete-orphan")
    cash_registers = relationship("CashRegister", back_populates="pharmacy", cascade="all, delete-orphan")
    cash_sessions = relationship("CashSession", back_populates="pharmacy", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="pharmacy", cascade="all, delete-orphan")
    product_categories = relationship("ProductCategory", back_populates="pharmacy", cascade="all, delete-orphan")
    credit_accounts = relationship("CustomerCreditAccount", back_populates="pharmacy", cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="pharmacy", cascade="all, delete-orphan")
    license = relationship("License", back_populates="pharmacy", uselist=False)
    
    # Pour la synchronisation
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_id = Column(String, unique=True, nullable=True)
