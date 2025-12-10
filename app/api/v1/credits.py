"""
Endpoints pour la gestion des crédits et dettes clients.
"""
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.deps import get_current_pharmacy_user
from app.db.base import get_db
from app.models.user import User
from app.models.customer import Customer
from app.models.credit import (
    CustomerCreditAccount,
    CreditTransaction,
    PaymentBreakdown,
    CreditTransactionType,
    PaymentBreakdownMethod,
)
from app.models.sale import Sale
from app.schemas.credit import (
    CustomerCreditAccount as CustomerCreditAccountSchema,
    CustomerCreditAccountCreate,
    CustomerCreditAccountUpdate,
    CreditTransaction as CreditTransactionSchema,
    CreditTransactionCreate,
    PayDebtRequest,
    CustomerCreditSummary,
    PharmacyCreditSummary,
    PaymentBreakdown as PaymentBreakdownSchema,
)
from app.core.logging import get_logger
from datetime import datetime
import uuid

router = APIRouter()
logger = get_logger(__name__)


# ============================================================
# Customer Credit Accounts
# ============================================================

@router.get("/accounts", response_model=List[CustomerCreditAccountSchema])
def list_credit_accounts(
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[int] = None,
    has_debt: Optional[bool] = None,  # True = seulement ceux avec dette
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste les comptes de crédit de la pharmacie."""
    query = db.query(CustomerCreditAccount).filter(
        CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id
    )
    
    if customer_id:
        query = query.filter(CustomerCreditAccount.customer_id == customer_id)
    
    if has_debt:
        query = query.filter(CustomerCreditAccount.current_balance > 0)
    
    accounts = query.offset(skip).limit(limit).all()
    return accounts


@router.get("/accounts/{account_id}", response_model=CustomerCreditAccountSchema)
def get_credit_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir un compte de crédit par ID."""
    account = db.query(CustomerCreditAccount).filter(
        CustomerCreditAccount.id == account_id,
        CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compte de crédit non trouvé"
        )
    
    return account


@router.post("/accounts", response_model=CustomerCreditAccountSchema, status_code=status.HTTP_201_CREATED)
def create_credit_account(
    account_in: CustomerCreditAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Créer un compte de crédit pour un client."""
    # Vérifier que le client existe et appartient à la pharmacie
    customer = db.query(Customer).filter(
        Customer.id == account_in.customer_id,
        Customer.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client non trouvé"
        )
    
    # Vérifier si un compte existe déjà
    existing = db.query(CustomerCreditAccount).filter(
        CustomerCreditAccount.customer_id == account_in.customer_id,
        CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte de crédit existe déjà pour ce client"
        )
    
    account = CustomerCreditAccount(
        pharmacy_id=current_user.pharmacy_id,
        customer_id=account_in.customer_id,
        credit_limit=account_in.credit_limit,
        notes=account_in.notes,
        is_active=account_in.is_active,
        current_balance=0.0
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    logger.info(f"Compte de crédit créé pour le client {account_in.customer_id}")
    return account


@router.put("/accounts/{account_id}", response_model=CustomerCreditAccountSchema)
def update_credit_account(
    account_id: int,
    account_in: CustomerCreditAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Mettre à jour un compte de crédit."""
    account = db.query(CustomerCreditAccount).filter(
        CustomerCreditAccount.id == account_id,
        CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compte de crédit non trouvé"
        )
    
    update_data = account_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    return account


# ============================================================
# Credit Transactions
# ============================================================

@router.get("/transactions", response_model=List[CreditTransactionSchema])
def list_credit_transactions(
    skip: int = 0,
    limit: int = 100,
    account_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    transaction_type: Optional[CreditTransactionType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste les transactions de crédit."""
    query = db.query(CreditTransaction).filter(
        CreditTransaction.pharmacy_id == current_user.pharmacy_id
    )
    
    if account_id:
        query = query.filter(CreditTransaction.account_id == account_id)
    
    if customer_id:
        # Filtrer par customer via account
        query = query.join(CustomerCreditAccount).filter(
            CustomerCreditAccount.customer_id == customer_id
        )
    
    if transaction_type:
        query = query.filter(CreditTransaction.transaction_type == transaction_type)
    
    transactions = query.order_by(CreditTransaction.created_at.desc()).offset(skip).limit(limit).all()
    return transactions


@router.get("/transactions/{transaction_id}", response_model=CreditTransactionSchema)
def get_credit_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir une transaction de crédit par ID."""
    transaction = db.query(CreditTransaction).filter(
        CreditTransaction.id == transaction_id,
        CreditTransaction.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction non trouvée"
        )
    
    return transaction


# ============================================================
# Pay Debt (Payer une dette)
# ============================================================

@router.post("/customers/{customer_id}/pay-debt", response_model=CreditTransactionSchema, status_code=status.HTTP_201_CREATED)
def pay_customer_debt(
    customer_id: int,
    payment_in: PayDebtRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Payer une dette d'un client."""
    # Vérifier que le client existe
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client non trouvé"
        )
    
    # Obtenir ou créer le compte de crédit
    account = db.query(CustomerCreditAccount).filter(
        CustomerCreditAccount.customer_id == customer_id,
        CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not account:
        # Créer le compte si il n'existe pas
        account = CustomerCreditAccount(
            pharmacy_id=current_user.pharmacy_id,
            customer_id=customer_id,
            current_balance=0.0
        )
        db.add(account)
        db.commit()
        db.refresh(account)
    
    # Vérifier que le client a une dette
    if account.current_balance <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce client n'a pas de dette"
        )
    
    # Vérifier que le montant à payer ne dépasse pas la dette
    if payment_in.amount > account.current_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le montant à payer ({payment_in.amount}) dépasse la dette ({account.current_balance})"
        )
    
    # Vérifier que la somme des paiements correspond au montant
    total_payments = sum(p.amount for p in payment_in.payment_breakdowns)
    if abs(total_payments - payment_in.amount) > 0.01:  # Tolérance pour les arrondis
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La somme des paiements ({total_payments}) ne correspond pas au montant ({payment_in.amount})"
        )
    
    # Créer la transaction de paiement
    new_balance = account.current_balance - payment_in.amount
    
    transaction = CreditTransaction(
        pharmacy_id=current_user.pharmacy_id,
        account_id=account.id,
        user_id=current_user.id,
        transaction_type=CreditTransactionType.PAYMENT,
        amount=payment_in.amount,
        balance_after=new_balance,
        reference_number=payment_in.reference_number or f"PAY-{uuid.uuid4().hex[:8].upper()}",
        notes=payment_in.notes
    )
    
    db.add(transaction)
    
    # Créer les payment breakdowns
    for payment_data in payment_in.payment_breakdowns:
        payment_breakdown = PaymentBreakdown(
            credit_transaction_id=transaction.id,
            payment_method=payment_data.payment_method,
            amount=payment_data.amount,
            reference=payment_data.reference,
            notes=payment_data.notes
        )
        db.add(payment_breakdown)
    
    # Mettre à jour le solde du compte
    account.current_balance = new_balance
    
    db.commit()
    db.refresh(transaction)
    
    logger.info(f"Paiement de dette effectué pour le client {customer_id}: {payment_in.amount}")
    return transaction


# ============================================================
# Summaries and Statistics
# ============================================================

@router.get("/customers/{customer_id}/summary", response_model=CustomerCreditSummary)
def get_customer_credit_summary(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir le résumé du crédit d'un client."""
    # Vérifier que le client existe
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client non trouvé"
        )
    
    # Obtenir le compte de crédit
    account = db.query(CustomerCreditAccount).filter(
        CustomerCreditAccount.customer_id == customer_id,
        CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not account:
        # Retourner un résumé avec solde à zéro
        return CustomerCreditSummary(
            customer_id=customer_id,
            customer_name=f"{customer.first_name} {customer.last_name}",
            current_balance=0.0,
            credit_limit=None,
            is_over_limit=False,
            last_transaction_date=None,
            total_owed=0.0
        )
    
    # Obtenir la dernière transaction
    last_transaction = db.query(CreditTransaction).filter(
        CreditTransaction.account_id == account.id
    ).order_by(CreditTransaction.created_at.desc()).first()
    
    is_over_limit = False
    if account.credit_limit and account.current_balance > account.credit_limit:
        is_over_limit = True
    
    return CustomerCreditSummary(
        customer_id=customer_id,
        customer_name=f"{customer.first_name} {customer.last_name}",
        current_balance=account.current_balance,
        credit_limit=account.credit_limit,
        is_over_limit=is_over_limit,
        last_transaction_date=last_transaction.created_at if last_transaction else None,
        total_owed=account.current_balance
    )


@router.get("/summary", response_model=PharmacyCreditSummary)
def get_pharmacy_credit_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir le résumé des crédits de la pharmacie."""
    # Calculer le total des dettes
    total_balance = db.query(func.sum(CustomerCreditAccount.current_balance)).filter(
        CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id,
        CustomerCreditAccount.current_balance > 0
    ).scalar() or 0.0
    
    # Compter les clients avec dette
    customers_with_debt = db.query(func.count(CustomerCreditAccount.id)).filter(
        CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id,
        CustomerCreditAccount.current_balance > 0
    ).scalar() or 0
    
    # Calculer le total des plafonds
    total_limit = db.query(func.sum(CustomerCreditAccount.credit_limit)).filter(
        CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id,
        CustomerCreditAccount.credit_limit.isnot(None)
    ).scalar()
    
    # Obtenir la liste des clients avec dette
    accounts_with_debt = db.query(CustomerCreditAccount).join(Customer).filter(
        CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id,
        CustomerCreditAccount.current_balance > 0
    ).all()
    
    customers = []
    for account in accounts_with_debt:
        customer = account.customer
        last_transaction = db.query(CreditTransaction).filter(
            CreditTransaction.account_id == account.id
        ).order_by(CreditTransaction.created_at.desc()).first()
        
        is_over_limit = False
        if account.credit_limit and account.current_balance > account.credit_limit:
            is_over_limit = True
        
        customers.append(CustomerCreditSummary(
            customer_id=customer.id,
            customer_name=f"{customer.first_name} {customer.last_name}",
            current_balance=account.current_balance,
            credit_limit=account.credit_limit,
            is_over_limit=is_over_limit,
            last_transaction_date=last_transaction.created_at if last_transaction else None,
            total_owed=account.current_balance
        ))
    
    return PharmacyCreditSummary(
        total_credit_balance=total_balance,
        total_customers_with_debt=customers_with_debt,
        total_credit_limit=total_limit,
        customers=customers
    )

