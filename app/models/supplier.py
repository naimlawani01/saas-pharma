from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False, index=True)
    
    # Informations fournisseur
    name = Column(String, nullable=False, index=True)
    contact_person = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    
    # Informations commerciales
    tax_id = Column(String, nullable=True)
    payment_terms = Column(String, nullable=True)  # Ex: "Net 30", "Cash on delivery"
    
    # Statut
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="suppliers")
    orders = relationship("SupplierOrder", back_populates="supplier", cascade="all, delete-orphan")
    
    # Pour la synchronisation
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_id = Column(String, unique=True, nullable=True)


class SupplierOrder(Base):
    __tablename__ = "supplier_orders"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Créateur de la commande
    
    # Informations commande
    order_number = Column(String, unique=True, nullable=False, index=True)
    order_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expected_delivery_date = Column(DateTime(timezone=True), nullable=True)
    delivery_date = Column(DateTime(timezone=True), nullable=True)
    
    # Montants
    subtotal = Column(Float, default=0.0, nullable=False)
    tax = Column(Float, default=0.0, nullable=False)
    shipping_cost = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, nullable=False)
    
    # Statut
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy")
    supplier = relationship("Supplier", back_populates="orders")
    items = relationship("SupplierOrderItem", back_populates="order", cascade="all, delete-orphan")
    
    # Pour la synchronisation
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_id = Column(String, unique=True, nullable=True)


class SupplierOrderItem(Base):
    __tablename__ = "supplier_order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("supplier_orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)  # Produit commandé
    
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0, nullable=False)
    unit_price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    
    # Gestion des substitutions et retours
    product_received_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # Produit réellement reçu (si différent)
    substitution_reason = Column(Text, nullable=True)  # Raison de la substitution
    is_returned = Column(Boolean, default=False, nullable=False)  # Produit retourné
    return_quantity = Column(Integer, default=0, nullable=False)  # Quantité retournée
    return_reason = Column(Text, nullable=True)  # Raison du retour
    return_date = Column(DateTime(timezone=True), nullable=True)  # Date du retour
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=True)  # Date de réception
    
    # Relations
    order = relationship("SupplierOrder", back_populates="items")
    product = relationship("Product", foreign_keys=[product_id], back_populates="supplier_order_items")
    product_received = relationship("Product", foreign_keys=[product_received_id])
