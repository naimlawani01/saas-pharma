from typing import Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from app.core.deps import get_current_pharmacy_user
from app.db.base import get_db
from app.models.user import User
from app.models.cash_register import (
    CashRegister,
    CashSession,
    CashTransaction,
    CashCount,
    CashSessionStatus,
    TransactionType,
    PaymentMethod,
)
from app.schemas.cash_register import (
    CashRegister as CashRegisterSchema,
    CashRegisterCreate,
    CashRegisterUpdate,
    CashSession as CashSessionSchema,
    CashSessionOpen,
    CashSessionClose,
    CashSessionWithDetails,
    CashTransaction as CashTransactionSchema,
    CashTransactionCreate,
    CashCount as CashCountSchema,
    CashRegisterStats,
    DailyCashReport,
)
import uuid

router = APIRouter()


# ============ CASH REGISTERS (Gestion des caisses) ============

@router.get("/registers", response_model=List[CashRegisterSchema])
def get_cash_registers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste toutes les caisses enregistreuses de la pharmacie."""
    registers = db.query(CashRegister).filter(
        CashRegister.pharmacy_id == current_user.pharmacy_id
    ).offset(skip).limit(limit).all()
    return registers


@router.post("/registers", response_model=CashRegisterSchema, status_code=status.HTTP_201_CREATED)
def create_cash_register(
    *,
    db: Session = Depends(get_db),
    register_in: CashRegisterCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Créer une nouvelle caisse enregistreuse."""
    if register_in.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create cash register for another pharmacy"
        )
    
    # Vérifier si le code existe déjà
    existing = db.query(CashRegister).filter(CashRegister.code == register_in.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cash register with this code already exists"
        )
    
    register = CashRegister(**register_in.model_dump())
    db.add(register)
    db.commit()
    db.refresh(register)
    return register


@router.get("/registers/{register_id}", response_model=CashRegisterSchema)
def get_cash_register(
    *,
    db: Session = Depends(get_db),
    register_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir une caisse par ID."""
    register = db.query(CashRegister).filter(
        CashRegister.id == register_id,
        CashRegister.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not register:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash register not found"
        )
    
    return register


@router.put("/registers/{register_id}", response_model=CashRegisterSchema)
def update_cash_register(
    *,
    db: Session = Depends(get_db),
    register_id: int,
    register_in: CashRegisterUpdate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Mettre à jour une caisse."""
    register = db.query(CashRegister).filter(
        CashRegister.id == register_id,
        CashRegister.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not register:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash register not found"
        )
    
    update_data = register_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(register, field, value)
    
    db.commit()
    db.refresh(register)
    return register


@router.delete("/registers/{register_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cash_register(
    *,
    db: Session = Depends(get_db),
    register_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> None:
    """Supprimer une caisse."""
    register = db.query(CashRegister).filter(
        CashRegister.id == register_id,
        CashRegister.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not register:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash register not found"
        )
    
    # Vérifier qu'il n'y a pas de session ouverte
    open_session = db.query(CashSession).filter(
        CashSession.cash_register_id == register_id,
        CashSession.status == CashSessionStatus.OPEN
    ).first()
    
    if open_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete cash register with an open session"
        )
    
    db.delete(register)
    db.commit()


# ============ CASH SESSIONS (Sessions de caisse) ============

@router.get("/sessions", response_model=List[CashSessionSchema])
def get_cash_sessions(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[CashSessionStatus] = None,
    cash_register_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste les sessions de caisse."""
    query = db.query(CashSession).filter(
        CashSession.pharmacy_id == current_user.pharmacy_id
    )
    
    if status_filter:
        query = query.filter(CashSession.status == status_filter)
    
    if cash_register_id:
        query = query.filter(CashSession.cash_register_id == cash_register_id)
    
    if start_date:
        query = query.filter(CashSession.opening_date >= start_date)
    
    if end_date:
        query = query.filter(CashSession.opening_date <= end_date)
    
    sessions = query.order_by(desc(CashSession.opening_date)).offset(skip).limit(limit).all()
    return sessions


@router.get("/sessions/current", response_model=Optional[CashSessionSchema])
def get_current_session(
    cash_register_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Récupère la session de caisse actuellement ouverte."""
    query = db.query(CashSession).filter(
        CashSession.pharmacy_id == current_user.pharmacy_id,
        CashSession.status == CashSessionStatus.OPEN
    )
    
    if cash_register_id:
        query = query.filter(CashSession.cash_register_id == cash_register_id)
    
    session = query.first()
    return session


@router.get("/sessions/{session_id}", response_model=CashSessionWithDetails)
def get_cash_session(
    *,
    db: Session = Depends(get_db),
    session_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Récupère une session de caisse avec tous les détails."""
    session = db.query(CashSession).filter(
        CashSession.id == session_id,
        CashSession.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash session not found"
        )
    
    return session


@router.post("/sessions/open", response_model=CashSessionSchema, status_code=status.HTTP_201_CREATED)
def open_cash_session(
    *,
    db: Session = Depends(get_db),
    session_in: CashSessionOpen,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Ouvrir une nouvelle session de caisse."""
    if session_in.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot open cash session for another pharmacy"
        )
    
    # Vérifier que la caisse existe
    cash_register = db.query(CashRegister).filter(
        CashRegister.id == session_in.cash_register_id,
        CashRegister.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not cash_register:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash register not found"
        )
    
    if not cash_register.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cash register is not active"
        )
    
    # Vérifier qu'il n'y a pas déjà une session ouverte pour cette caisse
    existing_session = db.query(CashSession).filter(
        CashSession.cash_register_id == session_in.cash_register_id,
        CashSession.status == CashSessionStatus.OPEN
    ).first()
    
    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A session is already open for this cash register"
        )
    
    # Générer un numéro de session unique
    session_number = f"CASH-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    # Créer la session
    session = CashSession(
        cash_register_id=session_in.cash_register_id,
        pharmacy_id=session_in.pharmacy_id,
        opened_by=current_user.id,
        session_number=session_number,
        status=CashSessionStatus.OPEN,
        opening_date=datetime.now(timezone.utc),
        opening_balance=session_in.opening_balance,
        opening_notes=session_in.opening_notes
    )
    
    db.add(session)
    db.flush()
    
    # Créer la transaction d'ouverture
    opening_transaction = CashTransaction(
        session_id=session.id,
        pharmacy_id=current_user.pharmacy_id,
        user_id=current_user.id,
        transaction_type=TransactionType.OPENING,
        payment_method=PaymentMethod.CASH,
        amount=session_in.opening_balance,
        description="Fond de caisse initial",
        notes=session_in.opening_notes
    )
    db.add(opening_transaction)
    
    db.commit()
    db.refresh(session)
    return session


@router.put("/sessions/{session_id}/close", response_model=CashSessionSchema)
def close_cash_session(
    *,
    db: Session = Depends(get_db),
    session_id: int,
    closing_data: CashSessionClose,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Fermer une session de caisse."""
    session = db.query(CashSession).filter(
        CashSession.id == session_id,
        CashSession.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash session not found"
        )
    
    if session.status == CashSessionStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cash session is already closed"
        )
    
    # Calculer les totaux attendus depuis les transactions
    transactions = db.query(CashTransaction).filter(
        CashTransaction.session_id == session_id
    ).all()
    
    expected_cash = session.opening_balance
    expected_card = 0.0
    expected_mobile_money = 0.0
    expected_check = 0.0
    
    for trans in transactions:
        if trans.transaction_type == TransactionType.SALE:
            if trans.payment_method == PaymentMethod.CASH:
                expected_cash += trans.amount
            elif trans.payment_method == PaymentMethod.CARD:
                expected_card += trans.amount
            elif trans.payment_method == PaymentMethod.MOBILE_MONEY:
                expected_mobile_money += trans.amount
            elif trans.payment_method == PaymentMethod.CHECK:
                expected_check += trans.amount
        elif trans.transaction_type in [TransactionType.REFUND, TransactionType.EXPENSE, TransactionType.WITHDRAWAL]:
            if trans.payment_method == PaymentMethod.CASH:
                expected_cash -= trans.amount
        elif trans.transaction_type == TransactionType.DEPOSIT:
            if trans.payment_method == PaymentMethod.CASH:
                expected_cash -= trans.amount
    
    # Calculer les écarts
    cash_difference = closing_data.cash_counted - expected_cash
    closing_balance = (closing_data.cash_counted + closing_data.card_total + 
                      closing_data.mobile_money_total + closing_data.check_total)
    expected_total = expected_cash + expected_card + expected_mobile_money + expected_check
    total_difference = closing_balance - expected_total
    
    # Mettre à jour la session
    session.status = CashSessionStatus.CLOSED
    session.closing_date = datetime.now(timezone.utc)
    session.closed_by = current_user.id
    session.cash_counted = closing_data.cash_counted
    session.card_total = closing_data.card_total
    session.mobile_money_total = closing_data.mobile_money_total
    session.check_total = closing_data.check_total
    session.closing_balance = closing_balance
    session.expected_cash = expected_cash
    session.expected_total = expected_total
    session.cash_difference = cash_difference
    session.total_difference = total_difference
    session.closing_notes = closing_data.closing_notes
    
    # Enregistrer le comptage détaillé si fourni
    if closing_data.cash_count:
        total_amount = (
            closing_data.cash_count.bills_20000 * 20000 +
            closing_data.cash_count.bills_10000 * 10000 +
            closing_data.cash_count.bills_5000 * 5000 +
            closing_data.cash_count.bills_2000 * 2000 +
            closing_data.cash_count.bills_1000 * 1000 +
            closing_data.cash_count.bills_500 * 500 +
            closing_data.cash_count.coins_500 * 500 +
            closing_data.cash_count.coins_100 * 100 +
            closing_data.cash_count.coins_50 * 50 +
            closing_data.cash_count.coins_25 * 25
        )
        
        cash_count = CashCount(
            session_id=session.id,
            **closing_data.cash_count.model_dump(),
            total_amount=total_amount
        )
        db.add(cash_count)
    
    db.commit()
    db.refresh(session)
    return session


# ============ CASH TRANSACTIONS (Transactions de caisse) ============

@router.get("/transactions", response_model=List[CashTransactionSchema])
def get_cash_transactions(
    session_id: Optional[int] = None,
    transaction_type: Optional[TransactionType] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste les transactions de caisse."""
    query = db.query(CashTransaction).filter(
        CashTransaction.pharmacy_id == current_user.pharmacy_id
    )
    
    if session_id:
        query = query.filter(CashTransaction.session_id == session_id)
    
    if transaction_type:
        query = query.filter(CashTransaction.transaction_type == transaction_type)
    
    transactions = query.order_by(desc(CashTransaction.created_at)).offset(skip).limit(limit).all()
    return transactions


@router.post("/transactions", response_model=CashTransactionSchema, status_code=status.HTTP_201_CREATED)
def create_cash_transaction(
    *,
    db: Session = Depends(get_db),
    transaction_in: CashTransactionCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Créer une transaction manuelle (dépense, retrait, etc.)."""
    # Vérifier que la session existe et est ouverte
    session = db.query(CashSession).filter(
        CashSession.id == transaction_in.session_id,
        CashSession.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash session not found"
        )
    
    if session.status != CashSessionStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cash session is not open"
        )
    
    transaction = CashTransaction(
        **transaction_in.model_dump(),
        pharmacy_id=current_user.pharmacy_id,
        user_id=current_user.id
    )
    
    db.add(transaction)
    
    # Mettre à jour les statistiques de la session
    if transaction_in.transaction_type == TransactionType.EXPENSE:
        session.total_expenses += transaction_in.amount
    elif transaction_in.transaction_type == TransactionType.REFUND:
        session.total_refunds += transaction_in.amount
    
    db.commit()
    db.refresh(transaction)
    return transaction


# ============ STATS & REPORTS ============

@router.get("/stats", response_model=CashRegisterStats)
def get_cash_register_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Statistiques globales des caisses."""
    pharmacy_id = current_user.pharmacy_id
    
    query = db.query(CashSession).filter(
        CashSession.pharmacy_id == pharmacy_id
    )
    
    if start_date:
        query = query.filter(CashSession.opening_date >= start_date)
    
    if end_date:
        query = query.filter(CashSession.opening_date <= end_date)
    
    sessions = query.all()
    
    total_sessions = len(sessions)
    open_sessions = len([s for s in sessions if s.status == CashSessionStatus.OPEN])
    closed_sessions = len([s for s in sessions if s.status == CashSessionStatus.CLOSED])
    
    total_sales_amount = sum(s.total_sales for s in sessions)
    total_cash_difference = sum(s.cash_difference or 0 for s in sessions if s.cash_difference is not None)
    average_session_amount = total_sales_amount / total_sessions if total_sessions > 0 else 0
    
    return CashRegisterStats(
        total_sessions=total_sessions,
        open_sessions=open_sessions,
        closed_sessions=closed_sessions,
        total_sales_amount=total_sales_amount,
        total_cash_difference=total_cash_difference,
        average_session_amount=average_session_amount
    )


@router.get("/reports/daily", response_model=DailyCashReport)
def get_daily_cash_report(
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Rapport de caisse journalier."""
    if date:
        target_date = datetime.fromisoformat(date).date()
    else:
        target_date = datetime.now(timezone.utc).date()
    
    # Récupérer toutes les sessions du jour
    sessions = db.query(CashSession).filter(
        CashSession.pharmacy_id == current_user.pharmacy_id,
        func.date(CashSession.opening_date) == target_date
    ).all()
    
    # Calculer les totaux
    total_sales = sum(s.total_sales for s in sessions)
    total_cash = sum(s.cash_counted or 0 for s in sessions)
    total_card = sum(s.card_total or 0 for s in sessions)
    total_mobile_money = sum(s.mobile_money_total or 0 for s in sessions)
    total_check = sum(s.check_total or 0 for s in sessions)
    total_difference = sum(s.total_difference or 0 for s in sessions)
    
    # Créer les résumés
    session_summaries = [
        {
            "session_id": s.id,
            "session_number": s.session_number,
            "status": s.status,
            "opening_date": s.opening_date,
            "closing_date": s.closing_date,
            "opening_balance": s.opening_balance,
            "closing_balance": s.closing_balance,
            "total_sales": s.total_sales,
            "total_refunds": s.total_refunds,
            "total_expenses": s.total_expenses,
            "sales_count": s.sales_count,
            "cash_difference": s.cash_difference,
            "total_difference": s.total_difference,
        }
        for s in sessions
    ]
    
    return DailyCashReport(
        date=target_date.isoformat(),
        sessions=session_summaries,
        total_sales=total_sales,
        total_cash=total_cash,
        total_card=total_card,
        total_mobile_money=total_mobile_money,
        total_check=total_check,
        total_difference=total_difference
    )

