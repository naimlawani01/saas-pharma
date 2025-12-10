"""
Schémas Pydantic pour la gestion des crédits et dettes clients.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.credit import CreditTransactionType, PaymentBreakdownMethod


# ============================================================
# CustomerCreditAccount Schemas
# ============================================================

class CustomerCreditAccountBase(BaseModel):
    credit_limit: Optional[float] = None
    notes: Optional[str] = None
    is_active: bool = True


class CustomerCreditAccountCreate(CustomerCreditAccountBase):
    customer_id: int
    credit_limit: Optional[float] = None


class CustomerCreditAccountUpdate(BaseModel):
    credit_limit: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerCreditAccount(CustomerCreditAccountBase):
    id: int
    pharmacy_id: int
    customer_id: int
    current_balance: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# PaymentBreakdown Schemas
# ============================================================

class PaymentBreakdownBase(BaseModel):
    payment_method: PaymentBreakdownMethod
    amount: float
    reference: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Le montant doit être positif")
        return v


class PaymentBreakdownCreate(PaymentBreakdownBase):
    pass


class PaymentBreakdown(PaymentBreakdownBase):
    id: int
    sale_id: int
    credit_transaction_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# CreditTransaction Schemas
# ============================================================

class CreditTransactionBase(BaseModel):
    transaction_type: CreditTransactionType
    amount: float
    notes: Optional[str] = None
    reference_number: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v, info):
        # Pour CHARGE, le montant doit être positif
        # Pour PAYMENT, le montant doit être positif (mais sera soustrait du solde)
        if v <= 0:
            raise ValueError("Le montant doit être positif")
        return v


class CreditTransactionCreate(CreditTransactionBase):
    account_id: int
    sale_id: Optional[int] = None
    payment_breakdowns: Optional[List[PaymentBreakdownCreate]] = None


class CreditTransactionUpdate(BaseModel):
    notes: Optional[str] = None


class CreditTransaction(CreditTransactionBase):
    id: int
    pharmacy_id: int
    account_id: int
    sale_id: Optional[int] = None
    user_id: int
    balance_after: float
    created_at: datetime
    payment_breakdowns: List[PaymentBreakdown] = []

    class Config:
        from_attributes = True


# ============================================================
# Schemas pour les paiements de dettes
# ============================================================

class PayDebtRequest(BaseModel):
    """Requête pour payer une dette."""
    amount: float
    payment_breakdowns: List[PaymentBreakdownCreate]
    notes: Optional[str] = None
    reference_number: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Le montant doit être positif")
        return v

    @field_validator("payment_breakdowns")
    @classmethod
    def validate_payment_breakdowns(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Au moins un paiement est requis")
        total = sum(p.amount for p in v)
        # On vérifiera que total == amount dans l'endpoint
        return v


# ============================================================
# Schemas pour les ventes avec paiements multiples
# ============================================================

class SalePaymentInfo(BaseModel):
    """Informations de paiement pour une vente."""
    payment_breakdowns: List[PaymentBreakdownCreate]
    credit_amount: float = 0.0  # Montant mis en crédit (reste à payer)
    notes: Optional[str] = None

    @field_validator("credit_amount")
    @classmethod
    def validate_credit_amount(cls, v):
        if v < 0:
            raise ValueError("Le montant de crédit ne peut pas être négatif")
        return v

    @field_validator("payment_breakdowns")
    @classmethod
    def validate_payment_breakdowns(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Au moins un paiement est requis")
        return v


# ============================================================
# Schemas pour les résumés et statistiques
# ============================================================

class CustomerCreditSummary(BaseModel):
    """Résumé du crédit d'un client."""
    customer_id: int
    customer_name: str
    current_balance: float
    credit_limit: Optional[float] = None
    is_over_limit: bool = False
    last_transaction_date: Optional[datetime] = None
    total_owed: float  # Alias pour current_balance (pour compatibilité)


class PharmacyCreditSummary(BaseModel):
    """Résumé des crédits de la pharmacie."""
    total_credit_balance: float
    total_customers_with_debt: int
    total_credit_limit: Optional[float] = None
    customers: List[CustomerCreditSummary] = []

