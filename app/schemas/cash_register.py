from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.cash_register import (
    CashSessionStatus,
    TransactionType,
    PaymentMethod,
)


# ============ Cash Register ============

class CashRegisterBase(BaseModel):
    name: str
    code: str
    location: Optional[str] = None
    is_active: bool = True


class CashRegisterCreate(CashRegisterBase):
    pharmacy_id: int


class CashRegisterUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class CashRegister(CashRegisterBase):
    id: int
    pharmacy_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Cash Count ============

class CashCountBase(BaseModel):
    bills_20000: int = 0
    bills_10000: int = 0
    bills_5000: int = 0
    bills_2000: int = 0
    bills_1000: int = 0
    bills_500: int = 0
    coins_500: int = 0
    coins_100: int = 0
    coins_50: int = 0
    coins_25: int = 0


class CashCountCreate(CashCountBase):
    pass


class CashCount(CashCountBase):
    id: int
    session_id: int
    total_amount: float
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Cash Session ============

class CashSessionBase(BaseModel):
    cash_register_id: int
    pharmacy_id: int


class CashSessionOpen(CashSessionBase):
    opening_balance: float = Field(..., ge=0, description="Fond de caisse initial")
    opening_notes: Optional[str] = None


class CashSessionClose(BaseModel):
    cash_counted: float = Field(..., ge=0, description="Espèces comptées")
    card_total: float = Field(default=0, ge=0)
    mobile_money_total: float = Field(default=0, ge=0)
    check_total: float = Field(default=0, ge=0)
    cash_count: Optional[CashCountCreate] = None
    closing_notes: Optional[str] = None


class CashSession(CashSessionBase):
    id: int
    session_number: str
    status: CashSessionStatus
    opened_by: int
    closed_by: Optional[int] = None
    
    # Ouverture
    opening_date: datetime
    opening_balance: float
    opening_notes: Optional[str] = None
    
    # Fermeture
    closing_date: Optional[datetime] = None
    closing_balance: Optional[float] = None
    cash_counted: Optional[float] = None
    card_total: Optional[float] = None
    mobile_money_total: Optional[float] = None
    check_total: Optional[float] = None
    
    # Calculés
    expected_cash: Optional[float] = None
    expected_total: Optional[float] = None
    cash_difference: Optional[float] = None
    total_difference: Optional[float] = None
    
    # Statistiques
    total_sales: float
    total_refunds: float
    total_expenses: float
    sales_count: int
    
    closing_notes: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CashSessionWithDetails(CashSession):
    """Session avec transactions et comptage détaillé."""
    transactions: List["CashTransaction"] = []
    cash_count: Optional[CashCount] = None


# ============ Cash Transaction ============

class CashTransactionBase(BaseModel):
    transaction_type: TransactionType
    payment_method: PaymentMethod
    amount: float = Field(..., description="Montant de la transaction")
    description: Optional[str] = None
    notes: Optional[str] = None


class CashTransactionCreate(CashTransactionBase):
    session_id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_number: Optional[str] = None


class CashTransaction(CashTransactionBase):
    id: int
    session_id: int
    pharmacy_id: int
    user_id: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_number: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Stats ============

class CashSessionSummary(BaseModel):
    """Résumé d'une session de caisse."""
    session_id: int
    session_number: str
    status: CashSessionStatus
    opening_date: datetime
    closing_date: Optional[datetime]
    opening_balance: float
    closing_balance: Optional[float]
    total_sales: float
    total_refunds: float
    total_expenses: float
    sales_count: int
    cash_difference: Optional[float]
    total_difference: Optional[float]


class CashRegisterStats(BaseModel):
    """Statistiques de caisse."""
    total_sessions: int
    open_sessions: int
    closed_sessions: int
    total_sales_amount: float
    total_cash_difference: float
    average_session_amount: float


class DailyCashReport(BaseModel):
    """Rapport de caisse journalier."""
    date: str
    sessions: List[CashSessionSummary]
    total_sales: float
    total_cash: float
    total_card: float
    total_mobile_money: float
    total_check: float
    total_difference: float

