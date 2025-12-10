"""
Modèles pour la gestion des crédits et dettes clients.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class CreditTransactionType(str, enum.Enum):
    """Type de transaction de crédit."""
    CHARGE = "charge"  # Création d'une dette (vente à crédit)
    PAYMENT = "payment"  # Paiement d'une dette
    ADJUSTMENT = "adjustment"  # Ajustement manuel (remise, annulation, etc.)
    REFUND = "refund"  # Remboursement


class PaymentBreakdownMethod(str, enum.Enum):
    """Méthode de paiement pour un paiement partiel."""
    CASH = "cash"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    CHECK = "check"
    BANK_TRANSFER = "bank_transfer"


class CustomerCreditAccount(Base):
    """Compte de crédit d'un client."""
    __tablename__ = "customer_credit_accounts"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Solde actuel (positif = dette du client)
    current_balance = Column(Float, default=0.0, nullable=False)
    
    # Plafond de crédit autorisé (optionnel, null = pas de limite)
    credit_limit = Column(Float, nullable=True)
    
    # Statut
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="credit_accounts")
    customer = relationship("Customer", back_populates="credit_account")
    transactions = relationship("CreditTransaction", back_populates="account", cascade="all, delete-orphan", order_by="CreditTransaction.created_at.desc()")
    
    # Pour la synchronisation
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_id = Column(String, unique=True, nullable=True)


class CreditTransaction(Base):
    """Transaction de crédit (charge ou paiement)."""
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    pharmacy_id = Column(Integer, ForeignKey("pharmacies.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("customer_credit_accounts.id"), nullable=False, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True, index=True)  # Si lié à une vente
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Utilisateur qui a effectué l'opération
    
    # Type de transaction
    transaction_type = Column(Enum(CreditTransactionType), nullable=False, index=True)
    
    # Montant (positif pour CHARGE, négatif pour PAYMENT)
    amount = Column(Float, nullable=False)
    
    # Solde après cette transaction
    balance_after = Column(Float, nullable=False)
    
    # Référence/Numéro de transaction
    reference_number = Column(String, nullable=True, index=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relations
    pharmacy = relationship("Pharmacy", back_populates="credit_transactions")
    account = relationship("CustomerCreditAccount", back_populates="transactions")
    sale = relationship("Sale", back_populates="credit_transactions")
    user = relationship("User")
    payment_breakdowns = relationship("PaymentBreakdown", back_populates="credit_transaction", cascade="all, delete-orphan")
    
    # Pour la synchronisation
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_id = Column(String, unique=True, nullable=True)


class PaymentBreakdown(Base):
    """Détail d'un paiement partiel (pour paiements multiples)."""
    __tablename__ = "payment_breakdowns"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False, index=True)
    credit_transaction_id = Column(Integer, ForeignKey("credit_transactions.id"), nullable=True, index=True)  # Si paiement d'une dette
    
    # Méthode de paiement
    payment_method = Column(Enum(PaymentBreakdownMethod), nullable=False)
    
    # Montant payé avec cette méthode
    amount = Column(Float, nullable=False)
    
    # Référence (numéro de chèque, référence mobile money, etc.)
    reference = Column(String, nullable=True)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relations
    sale = relationship("Sale", back_populates="payment_breakdowns")
    credit_transaction = relationship("CreditTransaction", back_populates="payment_breakdowns")
    
    # Pour la synchronisation
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_id = Column(String, unique=True, nullable=True)

