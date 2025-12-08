from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class MovementType(str, enum.Enum):
    """Types de mouvements de stock."""
    SALE = "sale"  # Vente
    PURCHASE = "purchase"  # Achat/Réception
    ADJUSTMENT = "adjustment"  # Ajustement manuel
    RETURN = "return"  # Retour client
    EXPIRY = "expiry"  # Produit expiré
    DAMAGE = "damage"  # Produit endommagé
    LOSS = "loss"  # Perte/Vol
    TRANSFER = "transfer"  # Transfert entre pharmacies


class StockMovement(Base):
    """Historique des mouvements de stock."""
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Type et quantité
    movement_type = Column(Enum(MovementType), nullable=False)
    quantity = Column(Integer, nullable=False)  # Positif = entrée, Négatif = sortie
    quantity_before = Column(Integer, nullable=False)  # Stock avant mouvement
    quantity_after = Column(Integer, nullable=False)  # Stock après mouvement
    
    # Référence (ID de vente, commande, etc.)
    reference_type = Column(String, nullable=True)  # "sale", "order", "adjustment"
    reference_id = Column(Integer, nullable=True)
    
    # Détails
    unit_cost = Column(Float, nullable=True)  # Coût unitaire
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="stock_movements")
    product = relationship("Product")
    user = relationship("User")


class AdjustmentReason(str, enum.Enum):
    """Raisons d'ajustement de stock."""
    INVENTORY = "inventory"  # Inventaire physique
    EXPIRY = "expiry"  # Produit expiré
    DAMAGE = "damage"  # Produit endommagé
    LOSS = "loss"  # Perte
    THEFT = "theft"  # Vol
    ERROR = "error"  # Erreur de saisie
    RETURN_SUPPLIER = "return_supplier"  # Retour fournisseur
    OTHER = "other"  # Autre raison


class StockAdjustment(Base):
    """Ajustements manuels de stock avec raisons."""
    __tablename__ = "stock_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Ajustement
    quantity_before = Column(Integer, nullable=False)
    quantity_adjusted = Column(Integer, nullable=False)  # Positif ou négatif
    quantity_after = Column(Integer, nullable=False)
    
    # Raison
    reason = Column(Enum(AdjustmentReason), nullable=False)
    notes = Column(Text, nullable=True)
    
    # Validation
    is_approved = Column(Boolean, default=True, nullable=False)  # Pour workflow d'approbation
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="stock_adjustments")
    product = relationship("Product", foreign_keys=[product_id])
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])


class AlertType(str, enum.Enum):
    """Types d'alertes."""
    LOW_STOCK = "low_stock"  # Stock faible
    OUT_OF_STOCK = "out_of_stock"  # Rupture de stock
    EXPIRING_SOON = "expiring_soon"  # Expire bientôt
    EXPIRED = "expired"  # Expiré
    OVERSTOCK = "overstock"  # Surstock


class AlertPriority(str, enum.Enum):
    """Priorité des alertes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    """Alertes du système."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # Peut être null pour alertes générales
    
    # Alerte
    alert_type = Column(Enum(AlertType), nullable=False)
    priority = Column(Enum(AlertPriority), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # État
    is_read = Column(Boolean, default=False, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="alerts")
    product = relationship("Product")
    resolver = relationship("User", foreign_keys=[resolved_by])


class Inventory(Base):
    """Inventaires périodiques."""
    __tablename__ = "inventories"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Inventaire
    inventory_number = Column(String, unique=True, nullable=False)
    inventory_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="in_progress", nullable=False)  # in_progress, completed, cancelled
    
    # Statistiques
    total_products_counted = Column(Integer, default=0, nullable=False)
    total_discrepancies = Column(Integer, default=0, nullable=False)
    
    notes = Column(Text, nullable=True)
    
    # Validation
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="inventories")
    user = relationship("User")
    items = relationship("InventoryItem", back_populates="inventory", cascade="all, delete-orphan")


class InventoryItem(Base):
    """Lignes d'inventaire (produits comptés)."""
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventories.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Quantités
    quantity_system = Column(Integer, nullable=False)  # Quantité dans le système
    quantity_counted = Column(Integer, nullable=False)  # Quantité comptée physiquement
    quantity_difference = Column(Integer, nullable=False)  # Différence (compté - système)
    
    notes = Column(Text, nullable=True)
    
    # Relations
    inventory = relationship("Inventory", back_populates="items")
    product = relationship("Product")

