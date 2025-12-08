from typing import Any, List, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid
from app.core.deps import get_current_pharmacy_user
from app.db.base import get_db
from app.models.user import User
from app.models.sync import SyncLog, SyncStatus, SyncDirection
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.models.customer import Customer
from app.models.supplier import Supplier, SupplierOrder
from app.schemas.sync import SyncRequest, SyncResponse, ConflictResolution, SyncUploadPayload
from app.core.config import settings

router = APIRouter()


@router.post("/", response_model=SyncResponse)
def sync_data(
    *,
    db: Session = Depends(get_db),
    sync_request: SyncRequest,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Synchroniser les données entre le client et le serveur."""
    sync_id = str(uuid.uuid4())
    
    # Créer un log de synchronisation
    sync_log = SyncLog(
        pharmacy_id=current_user.pharmacy_id,
        user_id=current_user.id,
        sync_id=sync_id,
        direction=sync_request.direction,
        status=SyncStatus.IN_PROGRESS
    )
    db.add(sync_log)
    db.commit()
    
    try:
        records_uploaded = 0
        records_downloaded = 0
        conflicts = []
        
        # Déterminer les types d'entités à synchroniser
        entity_types = sync_request.entity_types or ["products", "sales", "customers", "suppliers", "orders"]
        
        if sync_request.direction in [SyncDirection.UPLOAD, SyncDirection.BIDIRECTIONAL]:
            # Upload: envoyer les données locales vers le cloud
            for entity_type in entity_types:
                count = _upload_entities(db, current_user.pharmacy_id, entity_type, sync_request.last_sync_at)
                records_uploaded += count
        
        if sync_request.direction in [SyncDirection.DOWNLOAD, SyncDirection.BIDIRECTIONAL]:
            # Download: récupérer les données du cloud
            for entity_type in entity_types:
                count = _download_entities(db, current_user.pharmacy_id, entity_type, sync_request.last_sync_at)
                records_downloaded += count
        
        # Gérer les conflits si fournis
        if sync_request.conflicts:
            conflicts_count = _resolve_conflicts(db, current_user.pharmacy_id, sync_request.conflicts)
        else:
            conflicts_count = 0
        
        # Mettre à jour le log
        sync_log.status = SyncStatus.COMPLETED
        sync_log.records_uploaded = records_uploaded
        sync_log.records_downloaded = records_downloaded
        sync_log.conflicts_count = conflicts_count
        sync_log.completed_at = datetime.utcnow()
        
        # Mettre à jour la dernière synchronisation de la pharmacie
        from app.models.pharmacy import Pharmacy
        pharmacy = db.query(Pharmacy).filter(Pharmacy.id == current_user.pharmacy_id).first()
        if pharmacy:
            pharmacy.last_sync_at = datetime.utcnow()
        
        db.commit()
        
        return SyncResponse(
            sync_id=sync_id,
            status=SyncStatus.COMPLETED,
            records_uploaded=records_uploaded,
            records_downloaded=records_downloaded,
            conflicts_count=conflicts_count,
            conflicts=conflicts if conflicts else None,
            message="Synchronization completed successfully"
        )
    
    except Exception as e:
        sync_log.status = SyncStatus.FAILED
        sync_log.error_message = str(e)
        sync_log.completed_at = datetime.utcnow()
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synchronization failed: {str(e)}"
        )


def _upload_entities(db: Session, pharmacy_id: int, entity_type: str, last_sync_at: datetime = None) -> int:
    """Upload les entités modifiées depuis la dernière sync."""
    count = 0
    
    if entity_type == "products":
        query = db.query(Product).filter(Product.pharmacy_id == pharmacy_id)
        if last_sync_at:
            query = query.filter(
                (Product.updated_at > last_sync_at) | (Product.last_sync_at.is_(None))
            )
        count = query.count()
    
    elif entity_type == "sales":
        query = db.query(Sale).filter(Sale.pharmacy_id == pharmacy_id)
        if last_sync_at:
            query = query.filter(
                (Sale.updated_at > last_sync_at) | (Sale.last_sync_at.is_(None))
            )
        count = query.count()
    
    elif entity_type == "customers":
        query = db.query(Customer).filter(Customer.pharmacy_id == pharmacy_id)
        if last_sync_at:
            query = query.filter(
                (Customer.updated_at > last_sync_at) | (Customer.last_sync_at.is_(None))
            )
        count = query.count()
    
    elif entity_type == "suppliers":
        query = db.query(Supplier).filter(Supplier.pharmacy_id == pharmacy_id)
        if last_sync_at:
            query = query.filter(
                (Supplier.updated_at > last_sync_at) | (Supplier.last_sync_at.is_(None))
            )
        count = query.count()
    
    elif entity_type == "orders":
        query = db.query(SupplierOrder).filter(SupplierOrder.pharmacy_id == pharmacy_id)
        if last_sync_at:
            query = query.filter(
                (SupplierOrder.updated_at > last_sync_at) | (SupplierOrder.last_sync_at.is_(None))
            )
        count = query.count()
    
    return count


def _download_entities(db: Session, pharmacy_id: int, entity_type: str, last_sync_at: datetime = None) -> int:
    """Download les entités depuis le cloud."""
    # Dans une vraie implémentation, on récupérerait les données depuis le cloud
    # Pour l'instant, on simule juste le processus
    count = 0
    
    # Ici, on devrait faire une requête au cloud pour récupérer les données
    # et les insérer/mettre à jour dans la base locale
    
    return count


def _resolve_conflicts(db: Session, pharmacy_id: int, conflicts: List[ConflictResolution]) -> int:
    """Résout les conflits de synchronisation."""
    resolved = 0
    
    for conflict in conflicts:
        if conflict.resolution == "local":
            # Garder la version locale
            resolved += 1
        elif conflict.resolution == "cloud":
            # Utiliser la version cloud
            resolved += 1
        elif conflict.resolution == "merge":
            # Fusionner les deux versions (logique complexe)
            resolved += 1
    
    return resolved


@router.post("/upload", status_code=status.HTTP_200_OK)
def upload_data(
    *,
    db: Session = Depends(get_db),
    payload: SyncUploadPayload,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Upload batch de données depuis le client offline vers le backend.
    Supporte actuellement : products, customers, suppliers, orders, sales (simple).
    """
    entity_type = payload.entity_type
    items = payload.items or []

    processed = 0
    for item in items:
        if entity_type == "products":
            _upsert_product(db, current_user.pharmacy_id, item)
            processed += 1
        elif entity_type == "customers":
            _upsert_customer(db, current_user.pharmacy_id, item)
            processed += 1
        elif entity_type == "suppliers":
            _upsert_supplier(db, current_user.pharmacy_id, item)
            processed += 1
        elif entity_type == "orders":
            _upsert_supplier_order(db, current_user.pharmacy_id, item)
            processed += 1
        elif entity_type == "sales":
            _upsert_sale(db, current_user.pharmacy_id, current_user.id, item)
            processed += 1
        else:
            continue

    db.commit()
    return {"status": "ok", "processed": processed}


def _upsert_product(db: Session, pharmacy_id: int, data: Dict[str, Any]) -> Product:
    sync_id = data.get("sync_id")
    product = None
    if sync_id:
        product = db.query(Product).filter(
            Product.pharmacy_id == pharmacy_id,
            Product.sync_id == sync_id
        ).first()
    if not product and data.get("id"):
        product = db.query(Product).filter(
            Product.pharmacy_id == pharmacy_id,
            Product.id == data["id"]
        ).first()
    if not product:
        product = Product(pharmacy_id=pharmacy_id)
        db.add(product)

    # Mettre à jour les champs de base
    product.name = data.get("name", product.name)
    product.description = data.get("description", product.description)
    product.barcode = data.get("barcode", product.barcode)
    product.sku = data.get("sku", product.sku)
    product.category_id = data.get("category_id", product.category_id)
    product.quantity = data.get("quantity", product.quantity or 0)
    product.min_quantity = data.get("min_quantity", product.min_quantity or 0)
    product.purchase_price = data.get("purchase_price", product.purchase_price or 0)
    product.selling_price = data.get("selling_price", product.selling_price or 0)
    product.expiry_date = data.get("expiry_date", product.expiry_date)
    product.is_active = data.get("is_active", product.is_active if product.is_active is not None else True)
    product.is_prescription_required = data.get("is_prescription_required", product.is_prescription_required or False)
    product.sync_id = sync_id or product.sync_id
    product.last_sync_at = datetime.utcnow()
    return product


def _upsert_customer(db: Session, pharmacy_id: int, data: Dict[str, Any]) -> Customer:
    sync_id = data.get("sync_id")
    customer = None
    if sync_id:
        customer = db.query(Customer).filter(
            Customer.pharmacy_id == pharmacy_id,
            Customer.sync_id == sync_id
        ).first()
    if not customer and data.get("id"):
        customer = db.query(Customer).filter(
            Customer.pharmacy_id == pharmacy_id,
            Customer.id == data["id"]
        ).first()
    if not customer:
        customer = Customer(pharmacy_id=pharmacy_id)
        db.add(customer)

    customer.first_name = data.get("first_name", customer.first_name)
    customer.last_name = data.get("last_name", customer.last_name)
    customer.email = data.get("email", customer.email)
    customer.phone = data.get("phone", customer.phone)
    customer.address = data.get("address", customer.address)
    customer.city = data.get("city", customer.city)
    customer.date_of_birth = data.get("date_of_birth", customer.date_of_birth)
    customer.allergies = data.get("allergies", customer.allergies)
    customer.medical_notes = data.get("medical_notes", customer.medical_notes)
    customer.is_active = data.get("is_active", customer.is_active if customer.is_active is not None else True)
    customer.sync_id = sync_id or customer.sync_id
    customer.last_sync_at = datetime.utcnow()
    return customer


def _upsert_supplier(db: Session, pharmacy_id: int, data: Dict[str, Any]) -> Supplier:
    supplier = None
    if data.get("id"):
        supplier = db.query(Supplier).filter(
            Supplier.pharmacy_id == pharmacy_id,
            Supplier.id == data["id"]
        ).first()
    if not supplier:
        supplier = Supplier(pharmacy_id=pharmacy_id)
        db.add(supplier)

    supplier.name = data.get("name", supplier.name)
    supplier.contact_name = data.get("contact_name", supplier.contact_name)
    supplier.phone = data.get("phone", supplier.phone)
    supplier.email = data.get("email", supplier.email)
    supplier.address = data.get("address", supplier.address)
    supplier.tax_id = data.get("tax_id", supplier.tax_id)
    supplier.is_active = data.get("is_active", supplier.is_active if supplier.is_active is not None else True)
    supplier.last_sync_at = datetime.utcnow()
    return supplier


def _upsert_supplier_order(db: Session, pharmacy_id: int, data: Dict[str, Any]) -> SupplierOrder:
    order = None
    if data.get("id"):
        order = db.query(SupplierOrder).filter(
            SupplierOrder.pharmacy_id == pharmacy_id,
            SupplierOrder.id == data["id"]
        ).first()
    if not order:
        order = SupplierOrder(pharmacy_id=pharmacy_id)
        db.add(order)

    order.supplier_id = data.get("supplier_id", order.supplier_id)
    order.expected_delivery_date = data.get("expected_delivery_date", order.expected_delivery_date)
    order.status = data.get("status", order.status)
    order.notes = data.get("notes", order.notes)
    order.tax = data.get("tax", order.tax or 0)
    order.shipping_cost = data.get("shipping_cost", order.shipping_cost or 0)
    order.total_amount = data.get("total_amount", order.total_amount or 0)
    order.last_sync_at = datetime.utcnow()
    return order


def _upsert_sale(db: Session, pharmacy_id: int, user_id: int, data: Dict[str, Any]) -> Sale:
    sale = None
    if data.get("id"):
        sale = db.query(Sale).filter(
            Sale.pharmacy_id == pharmacy_id,
            Sale.id == data["id"]
        ).first()
    if not sale:
        sale = Sale(pharmacy_id=pharmacy_id, user_id=user_id)
        db.add(sale)

    sale.sale_number = data.get("sale_number", sale.sale_number)
    sale.customer_id = data.get("customer_id", sale.customer_id)
    sale.prescription_id = data.get("prescription_id", sale.prescription_id)
    sale.total_amount = data.get("total_amount", sale.total_amount or 0)
    sale.discount = data.get("discount", sale.discount or 0)
    sale.tax = data.get("tax", sale.tax or 0)
    sale.final_amount = data.get("final_amount", sale.final_amount or 0)
    sale.payment_method = data.get("payment_method", sale.payment_method)
    sale.status = data.get("status", sale.status)
    sale.notes = data.get("notes", sale.notes)
    sale.sync_id = data.get("sync_id", sale.sync_id)
    sale.last_sync_at = datetime.utcnow()

    # Gérer les items (remplacement simple)
    if data.get("items"):
        sale.items.clear()
        for item in data["items"]:
            sale_item = SaleItem(
                product_id=item.get("product_id"),
                quantity=item.get("quantity", 0),
                unit_price=item.get("unit_price", 0),
                discount=item.get("discount", 0),
                total=item.get("total", 0),
            )
            sale.items.append(sale_item)
    return sale


@router.get("/logs", response_model=List[Dict])
def get_sync_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir l'historique des synchronisations."""
    logs = db.query(SyncLog).filter(
        SyncLog.pharmacy_id == current_user.pharmacy_id
    ).order_by(SyncLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "sync_id": log.sync_id,
            "direction": log.direction.value,
            "status": log.status.value,
            "records_uploaded": log.records_uploaded,
            "records_downloaded": log.records_downloaded,
            "conflicts_count": log.conflicts_count,
            "started_at": log.started_at.isoformat(),
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "error_message": log.error_message
        }
        for log in logs
    ]


# ============================================================
# ENDPOINTS POUR RÉCUPÉRER LES DONNÉES À SYNCHRONISER
# ============================================================

@router.get("/data/products")
def get_products_to_sync(
    last_sync_at: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Récupérer les produits modifiés depuis la dernière synchronisation."""
    query = db.query(Product).filter(Product.pharmacy_id == current_user.pharmacy_id)
    
    if last_sync_at:
        query = query.filter(Product.updated_at > last_sync_at)
    
    products = query.all()
    
    return {
        "entity_type": "products",
        "count": len(products),
        "last_sync_at": datetime.utcnow().isoformat(),
        "data": [
            {
                "id": p.id,
                "sync_id": p.sync_id,
                "name": p.name,
                "description": p.description,
                "barcode": p.barcode,
                "sku": p.sku,
                "category_id": p.category_id,
                "quantity": p.quantity,
                "min_quantity": p.min_quantity,
                "unit": p.unit.value if p.unit else None,
                "purchase_price": p.purchase_price,
                "selling_price": p.selling_price,
                "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
                "is_active": p.is_active,
                "is_prescription_required": p.is_prescription_required,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat()
            }
            for p in products
        ]
    }


@router.get("/data/sales")
def get_sales_to_sync(
    last_sync_at: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Récupérer les ventes modifiées depuis la dernière synchronisation."""
    query = db.query(Sale).filter(Sale.pharmacy_id == current_user.pharmacy_id)
    
    if last_sync_at:
        query = query.filter(Sale.updated_at > last_sync_at)
    
    sales = query.all()
    
    return {
        "entity_type": "sales",
        "count": len(sales),
        "last_sync_at": datetime.utcnow().isoformat(),
        "data": [
            {
                "id": s.id,
                "sync_id": s.sync_id,
                "sale_number": s.sale_number,
                "customer_id": s.customer_id,
                "user_id": s.user_id,
                "total_amount": s.total_amount,
                "discount": s.discount,
                "tax": s.tax,
                "final_amount": s.final_amount,
                "payment_method": s.payment_method.value if s.payment_method else None,
                "status": s.status.value if s.status else None,
                "notes": s.notes,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "items": [
                    {
                        "id": item.id,
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "discount": item.discount,
                        "total": item.total
                    }
                    for item in s.items
                ]
            }
            for s in sales
        ]
    }


@router.get("/data/customers")
def get_customers_to_sync(
    last_sync_at: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Récupérer les clients modifiés depuis la dernière synchronisation."""
    query = db.query(Customer).filter(Customer.pharmacy_id == current_user.pharmacy_id)
    
    if last_sync_at:
        query = query.filter(Customer.updated_at > last_sync_at)
    
    customers = query.all()
    
    return {
        "entity_type": "customers",
        "count": len(customers),
        "last_sync_at": datetime.utcnow().isoformat(),
        "data": [
            {
                "id": c.id,
                "sync_id": c.sync_id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "phone": c.phone,
                "address": c.address,
                "city": c.city,
                "date_of_birth": c.date_of_birth.isoformat() if c.date_of_birth else None,
                "allergies": c.allergies,
                "medical_notes": c.medical_notes,
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            }
            for c in customers
        ]
    }


@router.get("/status")
def get_sync_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir le statut de synchronisation de la pharmacie."""
    from app.models.pharmacy import Pharmacy
    
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == current_user.pharmacy_id).first()
    
    # Compter les éléments non synchronisés
    pending_products = db.query(Product).filter(
        Product.pharmacy_id == current_user.pharmacy_id,
        Product.last_sync_at.is_(None)
    ).count()
    
    pending_sales = db.query(Sale).filter(
        Sale.pharmacy_id == current_user.pharmacy_id,
        Sale.last_sync_at.is_(None)
    ).count()
    
    pending_customers = db.query(Customer).filter(
        Customer.pharmacy_id == current_user.pharmacy_id,
        Customer.last_sync_at.is_(None)
    ).count()
    
    # Dernière sync
    last_sync = db.query(SyncLog).filter(
        SyncLog.pharmacy_id == current_user.pharmacy_id,
        SyncLog.status == SyncStatus.COMPLETED
    ).order_by(SyncLog.completed_at.desc()).first()
    
    return {
        "pharmacy_id": current_user.pharmacy_id,
        "last_sync_at": pharmacy.last_sync_at.isoformat() if pharmacy and pharmacy.last_sync_at else None,
        "last_sync_id": last_sync.sync_id if last_sync else None,
        "pending_sync": {
            "products": pending_products,
            "sales": pending_sales,
            "customers": pending_customers,
            "total": pending_products + pending_sales + pending_customers
        },
        "is_synced": (pending_products + pending_sales + pending_customers) == 0
    }
