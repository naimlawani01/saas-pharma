from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    CHECK = "check"
    CREDIT = "credit"


class SaleStatus(str, enum.Enum):
    COMPLETED = "completed"
    PENDING = "pending"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Vendeur
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)  # Prescription utilisée
    
    # Informations de vente
    sale_number = Column(String, unique=True, nullable=False, index=True)
    total_amount = Column(Float, nullable=False)
    discount = Column(Float, default=0.0, nullable=False)
    tax = Column(Float, default=0.0, nullable=False)
    final_amount = Column(Float, nullable=False)
    
    # Paiement
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH, nullable=False)
    status = Column(Enum(SaleStatus), default=SaleStatus.COMPLETED, nullable=False)
    
    # Notes
    notes = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")
    prescription = relationship("Prescription", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    
    # Pour la synchronisation
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_id = Column(String, unique=True, nullable=True)


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount = Column(Float, default=0.0, nullable=False)
    total = Column(Float, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relations
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")
