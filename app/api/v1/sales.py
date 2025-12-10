from typing import Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload
from app.core.deps import get_current_pharmacy_user
from app.db.base import get_db
from app.models.user import User, UserRole
from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.cash_register import CashSession, CashTransaction, CashSessionStatus, TransactionType, PaymentMethod as CashPaymentMethod
from app.models.credit import (
    CustomerCreditAccount,
    CreditTransaction,
    PaymentBreakdown,
    CreditTransactionType,
    PaymentBreakdownMethod,
)
from app.schemas.sale import Sale as SaleSchema, SaleCreate, SaleUpdate
from app.core.logging import get_logger
import uuid

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=List[SaleSchema])
def read_sales(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste les ventes de la pharmacie."""
    from app.models.sale import SaleStatus
    
    query = db.query(Sale).filter(Sale.pharmacy_id == current_user.pharmacy_id)
    
    # Filtrer par client si spécifié
    if customer_id is not None:
        query = query.filter(Sale.customer_id == customer_id)
    
    # Filtrer par statut si spécifié
    if status:
        try:
            sale_status = SaleStatus(status)
            query = query.filter(Sale.status == sale_status)
        except ValueError:
            # Statut invalide, ignorer
            pass
    
    # Filtrer par dates
    if start_date:
        query = query.filter(Sale.created_at >= start_date)
    if end_date:
        query = query.filter(Sale.created_at <= end_date)
    
    # Charger les relations (items et produits) pour éviter les requêtes N+1
    query = query.options(
        selectinload(Sale.items).selectinload(SaleItem.product)
    )
    
    # Pour l'historique client, augmenter la limite par défaut et ne pas limiter si customer_id est fourni
    if customer_id is not None:
        # Pour un client spécifique, retourner toutes ses ventes (ou au moins beaucoup plus)
        sales = query.order_by(Sale.created_at.desc()).offset(skip).limit(limit if limit > 100 else 1000).all()
    else:
        sales = query.order_by(Sale.created_at.desc()).offset(skip).limit(limit).all()
    
    return sales


@router.post("/", response_model=SaleSchema, status_code=status.HTTP_201_CREATED)
def create_sale(
    *,
    db: Session = Depends(get_db),
    sale_in: SaleCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Créer une nouvelle vente."""
    # Vérifier que la pharmacie correspond
    if sale_in.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create sale for another pharmacy"
        )
    
    # Calculer les totaux
    subtotal = sum(item.unit_price * item.quantity for item in sale_in.items)
    final_amount = subtotal - sale_in.discount + sale_in.tax
    
    # Gérer les paiements multiples et le crédit
    total_paid = 0.0
    credit_amount = sale_in.credit_amount or 0.0
    
    if sale_in.payment_breakdowns:
        # Calculer le total des paiements
        total_paid = sum(p.amount for p in sale_in.payment_breakdowns)
        
        # Vérifier que la somme des paiements + crédit = montant final
        if abs(total_paid + credit_amount - final_amount) > 0.01:  # Tolérance pour arrondis
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La somme des paiements ({total_paid}) + crédit ({credit_amount}) doit égaler le montant final ({final_amount})"
            )
    else:
        # Mode ancien : utiliser payment_method
        total_paid = final_amount - credit_amount
        if credit_amount > 0 and not sale_in.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un client est requis pour les ventes à crédit"
            )
    
    # Vérifier la prescription si fournie
    prescription = None
    if sale_in.prescription_id:
        from app.models.prescription import Prescription, PrescriptionStatus
        prescription = db.query(Prescription).options(
            selectinload(Prescription.items)
        ).filter(
            Prescription.id == sale_in.prescription_id,
            Prescription.pharmacy_id == current_user.pharmacy_id
        ).first()
        
        if not prescription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prescription not found"
            )
        
        if prescription.status not in [PrescriptionStatus.ACTIVE, PrescriptionStatus.PARTIALLY_USED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot use a {prescription.status.value} prescription"
            )
        
        # Vérifier la date d'expiration
        if prescription.expiry_date and prescription.expiry_date < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prescription has expired"
            )
    
    # Générer un numéro de vente unique
    sale_number = f"SALE-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    # Créer la vente
    sale = Sale(
        pharmacy_id=sale_in.pharmacy_id,
        customer_id=sale_in.customer_id,
        prescription_id=sale_in.prescription_id,
        user_id=current_user.id,
        sale_number=sale_number,
        total_amount=subtotal,
        discount=sale_in.discount,
        tax=sale_in.tax,
        final_amount=final_amount,
        payment_method=sale_in.payment_method,
        notes=sale_in.notes
    )
    
    db.add(sale)
    db.flush()  # Pour obtenir l'ID de la vente
    
    # Créer les items de vente et mettre à jour le stock
    for item_data in sale_in.items:
        product = db.query(Product).filter(
            Product.id == item_data.product_id,
            Product.pharmacy_id == current_user.pharmacy_id
        ).first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produit {item_data.product_id} non trouvé"
            )
        
        # Vérifier si le produit est actif
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le produit '{product.name}' n'est plus disponible à la vente"
            )
        
        # Vérifier le stock
        if product.quantity < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuffisant pour '{product.name}' (disponible: {product.quantity}, demandé: {item_data.quantity})"
            )
        
        # Vérifier si le produit nécessite une ordonnance
        if product.is_prescription_required:
            if not prescription:
                if current_user.role == UserRole.ASSISTANT:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Le produit '{product.name}' nécessite une ordonnance. Seul un pharmacien peut le vendre."
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Le produit '{product.name}' nécessite une ordonnance. Veuillez sélectionner une prescription."
                    )
            else:
                # Vérifier que le produit est dans la prescription
                prescription_item = next(
                    (item for item in prescription.items if item.product_id == product.id),
                    None
                )
                if not prescription_item:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Le produit '{product.name}' n'est pas dans la prescription sélectionnée"
                    )
                
                # Vérifier que la quantité ne dépasse pas la quantité prescrite restante
                remaining_quantity = prescription_item.quantity_prescribed - prescription_item.quantity_used
                if item_data.quantity > remaining_quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Quantité demandée ({item_data.quantity}) dépasse la quantité prescrite restante ({remaining_quantity}) pour '{product.name}'"
                    )
        
        # Vérifier la date d'expiration
        if product.expiry_date and product.expiry_date < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le produit '{product.name}' est expiré (date d'expiration: {product.expiry_date.strftime('%d/%m/%Y')})"
            )
        
        # Créer l'item
        item_total = (item_data.unit_price * item_data.quantity) - item_data.discount
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            discount=item_data.discount,
            total=item_total
        )
        db.add(sale_item)
        
        # Mettre à jour le stock
        product.quantity -= item_data.quantity
        
        # Vérifier et créer des alertes de stock si nécessaire
        from app.api.v1.stock import check_and_create_stock_alerts
        check_and_create_stock_alerts(db, product, current_user.pharmacy_id)
    
    # Gérer les paiements multiples et créer les payment breakdowns
    credit_transaction = None
    if sale_in.payment_breakdowns:
        # Créer les payment breakdowns pour la vente
        for payment_data in sale_in.payment_breakdowns:
            payment_breakdown = PaymentBreakdown(
                sale_id=sale.id,
                payment_method=payment_data.payment_method,
                amount=payment_data.amount,
                reference=payment_data.reference,
                notes=payment_data.notes
            )
            db.add(payment_breakdown)
    
    # Gérer le crédit si nécessaire
    if credit_amount > 0:
        if not sale_in.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un client est requis pour les ventes à crédit"
            )
        
        # Obtenir ou créer le compte de crédit
        account = db.query(CustomerCreditAccount).filter(
            CustomerCreditAccount.customer_id == sale_in.customer_id,
            CustomerCreditAccount.pharmacy_id == current_user.pharmacy_id
        ).first()
        
        if not account:
            # Créer le compte si il n'existe pas
            account = CustomerCreditAccount(
                pharmacy_id=current_user.pharmacy_id,
                customer_id=sale_in.customer_id,
                current_balance=0.0
            )
            db.add(account)
            db.flush()
        
        # Vérifier le plafond de crédit
        if account.credit_limit and (account.current_balance + credit_amount) > account.credit_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le plafond de crédit ({account.credit_limit}) serait dépassé (solde actuel: {account.current_balance}, nouveau crédit: {credit_amount})"
            )
        
        # Créer la transaction de crédit
        new_balance = account.current_balance + credit_amount
        credit_transaction = CreditTransaction(
            pharmacy_id=current_user.pharmacy_id,
            account_id=account.id,
            sale_id=sale.id,
            user_id=current_user.id,
            transaction_type=CreditTransactionType.CHARGE,
            amount=credit_amount,
            balance_after=new_balance,
            reference_number=f"CREDIT-{sale_number}",
            notes=f"Crédit pour vente {sale_number}"
        )
        db.add(credit_transaction)
        
        # Mettre à jour le solde du compte
        account.current_balance = new_balance
        
        logger.info(f"Crédit créé pour le client {sale_in.customer_id}: {credit_amount}")
    
    # Enregistrer les transactions dans la session de caisse ouverte
    current_session = db.query(CashSession).filter(
        CashSession.pharmacy_id == current_user.pharmacy_id,
        CashSession.status == CashSessionStatus.OPEN
    ).first()
    
    if current_session:
        if sale_in.payment_breakdowns:
            # Créer une transaction de caisse pour chaque paiement
            for payment_data in sale_in.payment_breakdowns:
                # Mapper les payment methods
                payment_method_mapping = {
                    PaymentBreakdownMethod.CASH: CashPaymentMethod.CASH,
                    PaymentBreakdownMethod.CARD: CashPaymentMethod.CARD,
                    PaymentBreakdownMethod.MOBILE_MONEY: CashPaymentMethod.MOBILE_MONEY,
                    PaymentBreakdownMethod.CHECK: CashPaymentMethod.CHECK,
                    PaymentBreakdownMethod.BANK_TRANSFER: CashPaymentMethod.CARD,  # Approximatif
                }
                
                cash_payment_method = payment_method_mapping.get(
                    payment_data.payment_method,
                    CashPaymentMethod.CASH
                )
                
                cash_transaction = CashTransaction(
                    session_id=current_session.id,
                    pharmacy_id=current_user.pharmacy_id,
                    user_id=current_user.id,
                    transaction_type=TransactionType.SALE,
                    payment_method=cash_payment_method,
                    amount=payment_data.amount,
                    reference_type="sale",
                    reference_id=sale.id,
                    reference_number=sale_number,
                    description=f"Vente {sale_number} - {payment_data.payment_method.value}",
                    notes=payment_data.notes
                )
                db.add(cash_transaction)
        else:
            # Mode ancien : une seule transaction
            payment_method_mapping = {
                "cash": CashPaymentMethod.CASH,
                "card": CashPaymentMethod.CARD,
                "mobile_money": CashPaymentMethod.MOBILE_MONEY,
                "check": CashPaymentMethod.CHECK,
                "credit": CashPaymentMethod.CREDIT,
            }
            
            cash_payment_method = payment_method_mapping.get(
                sale_in.payment_method.value if hasattr(sale_in.payment_method, 'value') else str(sale_in.payment_method),
                CashPaymentMethod.CASH
            )
            
            cash_transaction = CashTransaction(
                session_id=current_session.id,
                pharmacy_id=current_user.pharmacy_id,
                user_id=current_user.id,
                transaction_type=TransactionType.SALE,
                payment_method=cash_payment_method,
                amount=total_paid,  # Seulement le montant payé (pas le crédit)
                reference_type="sale",
                reference_id=sale.id,
                reference_number=sale_number,
                description=f"Vente {sale_number}",
                notes=sale_in.notes
            )
            db.add(cash_transaction)
        
        # Mettre à jour les statistiques de la session
        current_session.total_sales += total_paid  # Seulement les paiements réels
        current_session.sales_count += 1
    
    # Mettre à jour la prescription si utilisée
    if prescription:
        from app.models.prescription import PrescriptionStatus
        items_to_update = []
        for item_data in sale_in.items:
            prescription_item = next(
                (item for item in prescription.items if item.product_id == item_data.product_id),
                None
            )
            if prescription_item:
                prescription_item.quantity_used += item_data.quantity
                items_to_update.append({
                    "item_id": prescription_item.id,
                    "quantity": item_data.quantity
                })
        
        # Vérifier si tous les produits sont utilisés
        all_used = all(
            item.quantity_used >= item.quantity_prescribed
            for item in prescription.items
        )
        
        if all_used:
            prescription.status = PrescriptionStatus.USED
        else:
            prescription.status = PrescriptionStatus.PARTIALLY_USED
    
    db.commit()
    db.refresh(sale)
    return sale


@router.get("/{sale_id}", response_model=SaleSchema)
def read_sale(
    *,
    db: Session = Depends(get_db),
    sale_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir une vente par ID."""
    sale = db.query(Sale).filter(
        Sale.id == sale_id,
        Sale.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found"
        )
    
    return sale
