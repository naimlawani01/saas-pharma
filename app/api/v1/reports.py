from typing import Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.core.deps import get_current_pharmacy_user
from app.db.base import get_db
from app.models.user import User
from app.models.sale import Sale, SaleItem, SaleStatus
from app.models.product import Product
from app.models.customer import Customer
from app.models.supplier import SupplierOrder

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir les statistiques du tableau de bord."""
    pharmacy_id = current_user.pharmacy_id
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    start_of_month = datetime(today.year, today.month, 1)
    
    # Ventes du jour
    daily_sales = db.query(func.sum(Sale.final_amount)).filter(
        Sale.pharmacy_id == pharmacy_id,
        Sale.status == SaleStatus.COMPLETED,
        Sale.created_at >= start_of_day
    ).scalar() or 0
    
    daily_sales_count = db.query(func.count(Sale.id)).filter(
        Sale.pharmacy_id == pharmacy_id,
        Sale.status == SaleStatus.COMPLETED,
        Sale.created_at >= start_of_day
    ).scalar() or 0
    
    # Ventes du mois
    monthly_sales = db.query(func.sum(Sale.final_amount)).filter(
        Sale.pharmacy_id == pharmacy_id,
        Sale.status == SaleStatus.COMPLETED,
        Sale.created_at >= start_of_month
    ).scalar() or 0
    
    monthly_sales_count = db.query(func.count(Sale.id)).filter(
        Sale.pharmacy_id == pharmacy_id,
        Sale.status == SaleStatus.COMPLETED,
        Sale.created_at >= start_of_month
    ).scalar() or 0
    
    # Produits en stock critique
    low_stock_count = db.query(func.count(Product.id)).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True,
        Product.quantity <= Product.min_quantity
    ).scalar() or 0
    
    # Produits expirés ou bientôt expirés (30 jours)
    expiry_threshold = datetime.utcnow() + timedelta(days=30)
    expiring_soon_count = db.query(func.count(Product.id)).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True,
        Product.expiry_date != None,
        Product.expiry_date <= expiry_threshold
    ).scalar() or 0
    
    # Total produits
    total_products = db.query(func.count(Product.id)).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True
    ).scalar() or 0
    
    # Total clients
    total_customers = db.query(func.count(Customer.id)).filter(
        Customer.pharmacy_id == pharmacy_id,
        Customer.is_active == True
    ).scalar() or 0
    
    # Valeur totale du stock
    stock_value = db.query(func.sum(Product.quantity * Product.purchase_price)).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True
    ).scalar() or 0
    
    return {
        "daily_sales": {
            "amount": float(daily_sales),
            "count": daily_sales_count
        },
        "monthly_sales": {
            "amount": float(monthly_sales),
            "count": monthly_sales_count
        },
        "inventory": {
            "total_products": total_products,
            "low_stock_count": low_stock_count,
            "expiring_soon_count": expiring_soon_count,
            "stock_value": float(stock_value)
        },
        "customers": {
            "total": total_customers
        }
    }


@router.get("/sales-by-period")
def get_sales_by_period(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    group_by: str = "day",  # day, week, month
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir les ventes groupées par période."""
    pharmacy_id = current_user.pharmacy_id
    
    # Par défaut, 30 derniers jours
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Construire la requête selon le groupement
    if group_by == "day":
        date_trunc = func.date(Sale.created_at)
    elif group_by == "week":
        date_trunc = func.date_trunc('week', Sale.created_at)
    elif group_by == "month":
        date_trunc = func.date_trunc('month', Sale.created_at)
    else:
        date_trunc = func.date(Sale.created_at)
    
    results = db.query(
        date_trunc.label('period'),
        func.count(Sale.id).label('count'),
        func.sum(Sale.final_amount).label('total')
    ).filter(
        Sale.pharmacy_id == pharmacy_id,
        Sale.status == SaleStatus.COMPLETED,
        Sale.created_at >= start_date,
        Sale.created_at <= end_date
    ).group_by(date_trunc).order_by(date_trunc).all()
    
    return [
        {
            "period": str(r.period),
            "count": r.count,
            "total": float(r.total) if r.total else 0
        }
        for r in results
    ]


@router.get("/top-products")
def get_top_products(
    limit: int = 10,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir les produits les plus vendus."""
    pharmacy_id = current_user.pharmacy_id
    
    # Par défaut, 30 derniers jours
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    results = db.query(
        Product.id,
        Product.name,
        func.sum(SaleItem.quantity).label('total_quantity'),
        func.sum(SaleItem.total).label('total_revenue')
    ).join(
        SaleItem, SaleItem.product_id == Product.id
    ).join(
        Sale, Sale.id == SaleItem.sale_id
    ).filter(
        Sale.pharmacy_id == pharmacy_id,
        Sale.status == SaleStatus.COMPLETED,
        Sale.created_at >= start_date,
        Sale.created_at <= end_date
    ).group_by(
        Product.id, Product.name
    ).order_by(
        func.sum(SaleItem.quantity).desc()
    ).limit(limit).all()
    
    return [
        {
            "product_id": r.id,
            "product_name": r.name,
            "total_quantity": int(r.total_quantity),
            "total_revenue": float(r.total_revenue) if r.total_revenue else 0
        }
        for r in results
    ]


@router.get("/low-stock")
def get_low_stock_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir les produits en stock critique."""
    pharmacy_id = current_user.pharmacy_id
    
    products = db.query(Product).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True,
        Product.quantity <= Product.min_quantity
    ).order_by(Product.quantity.asc()).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "quantity": p.quantity,
            "min_quantity": p.min_quantity,
            "deficit": p.min_quantity - p.quantity,
            "selling_price": p.selling_price
        }
        for p in products
    ]


@router.get("/expiring-products")
def get_expiring_products(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir les produits qui vont expirer bientôt."""
    pharmacy_id = current_user.pharmacy_id
    expiry_threshold = datetime.utcnow() + timedelta(days=days)
    
    products = db.query(Product).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True,
        Product.expiry_date != None,
        Product.expiry_date <= expiry_threshold,
        Product.quantity > 0
    ).order_by(Product.expiry_date.asc()).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "quantity": p.quantity,
            "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
            "days_until_expiry": (p.expiry_date - datetime.utcnow()).days if p.expiry_date else None,
            "is_expired": p.expiry_date < datetime.utcnow() if p.expiry_date else False,
            "stock_value": p.quantity * p.purchase_price
        }
        for p in products
    ]


@router.get("/sales-by-payment-method")
def get_sales_by_payment_method(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir les ventes groupées par méthode de paiement."""
    pharmacy_id = current_user.pharmacy_id
    
    # Par défaut, 30 derniers jours
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    results = db.query(
        Sale.payment_method,
        func.count(Sale.id).label('count'),
        func.sum(Sale.final_amount).label('total')
    ).filter(
        Sale.pharmacy_id == pharmacy_id,
        Sale.status == SaleStatus.COMPLETED,
        Sale.created_at >= start_date,
        Sale.created_at <= end_date
    ).group_by(Sale.payment_method).all()
    
    return [
        {
            "payment_method": r.payment_method.value,
            "count": r.count,
            "total": float(r.total) if r.total else 0
        }
        for r in results
    ]


@router.get("/top-customers")
def get_top_customers(
    limit: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir les meilleurs clients."""
    from datetime import date as date_type
    
    pharmacy_id = current_user.pharmacy_id
    
    # Construire la requête
    # Important: utiliser inner join pour exclure les ventes sans client (customer_id IS NULL)
    query = db.query(
        Customer.id,
        Customer.first_name,
        Customer.last_name,
        Customer.phone,
        func.count(Sale.id).label('purchase_count'),
        func.sum(Sale.final_amount).label('total_spent')
    ).join(
        Sale, Sale.customer_id == Customer.id
    ).filter(
        Sale.pharmacy_id == pharmacy_id,
        Sale.status == SaleStatus.COMPLETED,
        Sale.customer_id.isnot(None)  # Exclure explicitement les ventes sans client
    )
    
    # Appliquer les filtres de date seulement s'ils sont fournis
    # Convertir les dates string en datetime si nécessaire
    if start_date:
        try:
            # Si c'est une date simple (YYYY-MM-DD), inclure toute la journée (début à 00:00:00 UTC)
            if isinstance(start_date, str) and len(start_date) == 10:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                # Convertir en UTC timezone-aware
                start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                # Si les dates dans la DB sont timezone-aware, on doit aussi rendre start_dt timezone-aware
                from datetime import timezone
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            else:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Sale.created_at >= start_dt)
        except (ValueError, AttributeError) as e:
            # Si le parsing échoue, ignorer le filtre
            import logging
            logging.warning(f"Error parsing start_date {start_date}: {e}")
            pass
    
    if end_date:
        try:
            # Si c'est une date simple (YYYY-MM-DD), inclure toute la journée (jusqu'à 23:59:59 UTC)
            if isinstance(end_date, str) and len(end_date) == 10:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                # Convertir en UTC timezone-aware
                from datetime import timezone
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            else:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Sale.created_at <= end_dt)
        except (ValueError, AttributeError) as e:
            # Si le parsing échoue, ignorer le filtre
            import logging
            logging.warning(f"Error parsing end_date {end_date}: {e}")
            pass
    
    results = query.group_by(
        Customer.id, Customer.first_name, Customer.last_name, Customer.phone
    ).order_by(
        func.sum(Sale.final_amount).desc()
    ).limit(limit).all()
    
    # Debug: logger les résultats pour vérification
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Top customers query - start_date: {start_date}, end_date: {end_date}, results count: {len(results)}")
    
    return [
        {
            "customer_id": r.id,
            "name": f"{r.first_name} {r.last_name}",
            "phone": r.phone,
            "purchase_count": int(r.purchase_count) if r.purchase_count else 0,
            "total_spent": float(r.total_spent) if r.total_spent else 0.0
        }
        for r in results
    ]

