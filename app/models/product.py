from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="product_categories")
    
    # Contrainte unique : nom unique par pharmacie
    __table_args__ = (
        UniqueConstraint('pharmacy_id', 'name', name='uq_product_category_pharmacy_name'),
    )


class ProductUnit(str, enum.Enum):
    UNIT = "unit"
    BOX = "box"
    BOTTLE = "bottle"
    STRIP = "strip"
    PACK = "pack"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False, index=True)
    
    # Informations produit
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    barcode = Column(String, unique=True, nullable=True, index=True)
    sku = Column(String, nullable=True, index=True)  # Stock Keeping Unit
    
    # Catégorie
    category_id = Column(Integer, ForeignKey("product_categories.id"), nullable=True)
    category = relationship("ProductCategory")
    
    # Stock
    quantity = Column(Integer, default=0, nullable=False)
    min_quantity = Column(Integer, default=0, nullable=False)  # Seuil d'alerte
    unit = Column(Enum(ProductUnit), default=ProductUnit.UNIT, nullable=False)
    
    # Prix
    purchase_price = Column(Float, nullable=False)  # Prix d'achat
    selling_price = Column(Float, nullable=False)  # Prix de vente
    
    # Dates importantes
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    manufacturing_date = Column(DateTime(timezone=True), nullable=True)
    
    # Statut
    is_active = Column(Boolean, default=True, nullable=False)
    is_prescription_required = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="products")
    sale_items = relationship("SaleItem", back_populates="product")
    supplier_order_items = relationship("SupplierOrderItem", foreign_keys="SupplierOrderItem.product_id", back_populates="product")
    
    # Pour la synchronisation
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_id = Column(String, unique=True, nullable=True)
