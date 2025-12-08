from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class CashSessionStatus(str, enum.Enum):
    """Statut de la session de caisse."""
    OPEN = "open"  # Caisse ouverte
    CLOSED = "closed"  # Caisse fermée


class TransactionType(str, enum.Enum):
    """Types de transactions de caisse."""
    OPENING = "opening"  # Fond de caisse initial
    SALE = "sale"  # Vente
    REFUND = "refund"  # Remboursement
    EXPENSE = "expense"  # Dépense
    DEPOSIT = "deposit"  # Dépôt en banque
    WITHDRAWAL = "withdrawal"  # Retrait
    CORRECTION = "correction"  # Correction d'écart


class PaymentMethod(str, enum.Enum):
    """Méthodes de paiement."""
    CASH = "cash"  # Espèces
    CARD = "card"  # Carte bancaire
    MOBILE_MONEY = "mobile_money"  # Mobile Money
    CHECK = "check"  # Chèque
    CREDIT = "credit"  # Crédit


class CashRegister(Base):
    """Caisse enregistreuse (équipement physique)."""
    __tablename__ = "cash_registers"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    
    # Informations
    name = Column(String, nullable=False)  # Ex: "Caisse 1", "Caisse principale"
    code = Column(String, unique=True, nullable=False)  # Code unique
    location = Column(String, nullable=True)  # Emplacement dans la pharmacie
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="cash_registers")
    sessions = relationship("CashSession", back_populates="cash_register", cascade="all, delete-orphan")


class CashSession(Base):
    """Session de caisse (ouverture/fermeture journalière)."""
    __tablename__ = "cash_sessions"

    id = Column(Integer, primary_key=True, index=True)
    cash_register_id = Column(Integer, ForeignKey("cash_registers.id"), nullable=False)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    opened_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    closed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Session
    session_number = Column(String, unique=True, nullable=False)
    status = Column(Enum(CashSessionStatus), default=CashSessionStatus.OPEN, nullable=False)
    
    # Ouverture
    opening_date = Column(DateTime(timezone=True), nullable=False)
    opening_balance = Column(Float, default=0.0, nullable=False)  # Fond de caisse initial
    opening_notes = Column(Text, nullable=True)
    
    # Fermeture
    closing_date = Column(DateTime(timezone=True), nullable=True)
    closing_balance = Column(Float, nullable=True)  # Montant compté à la fermeture
    
    # Détails de fermeture par méthode de paiement
    cash_counted = Column(Float, default=0.0, nullable=True)  # Espèces comptées
    card_total = Column(Float, default=0.0, nullable=True)  # Total carte
    mobile_money_total = Column(Float, default=0.0, nullable=True)  # Total Mobile Money
    check_total = Column(Float, default=0.0, nullable=True)  # Total chèques
    
    # Totaux calculés (du système)
    expected_cash = Column(Float, nullable=True)  # Espèces attendues
    expected_total = Column(Float, nullable=True)  # Total attendu
    
    # Écart
    cash_difference = Column(Float, default=0.0, nullable=True)  # Écart espèces
    total_difference = Column(Float, default=0.0, nullable=True)  # Écart total
    
    # Statistiques de la session
    total_sales = Column(Float, default=0.0, nullable=False)  # Total des ventes
    total_refunds = Column(Float, default=0.0, nullable=False)  # Total remboursements
    total_expenses = Column(Float, default=0.0, nullable=False)  # Total dépenses
    sales_count = Column(Integer, default=0, nullable=False)  # Nombre de ventes
    
    closing_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    cash_register = relationship("CashRegister", back_populates="sessions")
    pharmacy = relationship("Pharmacy", back_populates="cash_sessions")
    opener = relationship("User", foreign_keys=[opened_by])
    closer = relationship("User", foreign_keys=[closed_by])
    transactions = relationship("CashTransaction", back_populates="session", cascade="all, delete-orphan")


class CashTransaction(Base):
    """Transaction de caisse individuelle."""
    __tablename__ = "cash_transactions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("cash_sessions.id"), nullable=False)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Transaction
    transaction_type = Column(Enum(TransactionType), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    amount = Column(Float, nullable=False)
    
    # Références
    reference_type = Column(String, nullable=True)  # "sale", "refund", "expense"
    reference_id = Column(Integer, nullable=True)  # ID de la vente, remboursement, etc.
    reference_number = Column(String, nullable=True)  # Numéro de référence
    
    # Détails
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relations
    session = relationship("CashSession", back_populates="transactions")
    pharmacy = relationship("Pharmacy")
    user = relationship("User")


class CashCount(Base):
    """Comptage détaillé des espèces (billets et pièces)."""
    __tablename__ = "cash_counts"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("cash_sessions.id"), nullable=False)
    
    # Comptage par dénomination (exemple pour Franc Guinéen)
    bills_20000 = Column(Integer, default=0, nullable=False)  # Billets de 20000 GNF
    bills_10000 = Column(Integer, default=0, nullable=False)  # Billets de 10000 GNF
    bills_5000 = Column(Integer, default=0, nullable=False)   # Billets de 5000 GNF
    bills_2000 = Column(Integer, default=0, nullable=False)   # Billets de 2000 GNF
    bills_1000 = Column(Integer, default=0, nullable=False)   # Billets de 1000 GNF
    bills_500 = Column(Integer, default=0, nullable=False)    # Billets de 500 GNF
    
    coins_500 = Column(Integer, default=0, nullable=False)    # Pièces de 500 GNF
    coins_100 = Column(Integer, default=0, nullable=False)    # Pièces de 100 GNF
    coins_50 = Column(Integer, default=0, nullable=False)     # Pièces de 50 GNF
    coins_25 = Column(Integer, default=0, nullable=False)     # Pièces de 25 GNF
    
    # Total calculé
    total_amount = Column(Float, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relation
    session = relationship("CashSession")

