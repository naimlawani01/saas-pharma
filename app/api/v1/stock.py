from typing import Any, List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, desc
from app.core.deps import get_current_pharmacy_user
from app.db.base import get_db
from app.models.user import User
from app.models.stock import (
    StockMovement,
    StockAdjustment,
    Alert,
    Inventory,
    InventoryItem,
    MovementType,
    AdjustmentReason,
    AlertType,
    AlertPriority,
)
from app.models.product import Product
from app.schemas.stock import (
    StockMovement as StockMovementSchema,
    StockAdjustment as StockAdjustmentSchema,
    StockAdjustmentCreate,
    StockAdjustmentUpdate,
    Alert as AlertSchema,
    AlertCreate,
    AlertUpdate,
    Inventory as InventorySchema,
    InventoryCreate,
    InventoryUpdate,
    StockStats,
    AlertStats,
)
import uuid

router = APIRouter()


# ============ STOCK MOVEMENTS (Historique) ============

@router.get("/movements", response_model=List[StockMovementSchema])
def get_stock_movements(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[int] = None,
    movement_type: Optional[MovementType] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Récupérer l'historique des mouvements de stock.
    """
    query = db.query(StockMovement).filter(
        StockMovement.pharmacy_id == current_user.pharmacy_id
    )
    
    if product_id:
        query = query.filter(StockMovement.product_id == product_id)
    
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)
    
    if start_date:
        query = query.filter(StockMovement.created_at >= start_date)
    
    if end_date:
        query = query.filter(StockMovement.created_at <= end_date)
    
    movements = query.options(
        selectinload(StockMovement.product),
        selectinload(StockMovement.user)
    ).order_by(desc(StockMovement.created_at)).offset(skip).limit(limit).all()
    return movements


@router.get("/movements/stats", response_model=StockStats)
def get_stock_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Statistiques de stock pour le dashboard.
    """
    pharmacy_id = current_user.pharmacy_id
    
    # Total produits
    total_products = db.query(Product).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True
    ).count()
    
    # Produits en stock bas
    low_stock_count = db.query(Product).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True,
        Product.quantity <= Product.min_quantity,
        Product.quantity > 0
    ).count()
    
    # Rupture de stock
    out_of_stock_count = db.query(Product).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True,
        Product.quantity <= 0
    ).count()
    
    # Produits expirant dans 30 jours
    thirty_days_from_now = datetime.now(timezone.utc) + timedelta(days=30)
    expiring_soon_count = db.query(Product).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True,
        Product.expiry_date.isnot(None),
        Product.expiry_date <= thirty_days_from_now,
        Product.expiry_date > datetime.now(timezone.utc)
    ).count()
    
    # Produits expirés
    expired_count = db.query(Product).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True,
        Product.expiry_date.isnot(None),
        Product.expiry_date <= datetime.now(timezone.utc)
    ).count()
    
    # Valeur totale du stock
    products = db.query(Product).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True
    ).all()
    total_value = sum(p.selling_price * p.quantity for p in products)
    
    return StockStats(
        total_products=total_products,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,
        expiring_soon_count=expiring_soon_count,
        expired_count=expired_count,
        total_value=total_value
    )


# ============ STOCK ADJUSTMENTS ============

@router.get("/adjustments", response_model=List[StockAdjustmentSchema])
def get_stock_adjustments(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[int] = None,
    reason: Optional[AdjustmentReason] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Récupérer les ajustements de stock.
    """
    query = db.query(StockAdjustment).filter(
        StockAdjustment.pharmacy_id == current_user.pharmacy_id
    )
    
    if product_id:
        query = query.filter(StockAdjustment.product_id == product_id)
    
    if reason:
        query = query.filter(StockAdjustment.reason == reason)
    
    adjustments = query.options(
        selectinload(StockAdjustment.product),
        selectinload(StockAdjustment.user)
    ).order_by(desc(StockAdjustment.created_at)).offset(skip).limit(limit).all()
    return adjustments


@router.post("/adjustments", response_model=StockAdjustmentSchema, status_code=status.HTTP_201_CREATED)
def create_stock_adjustment(
    *,
    db: Session = Depends(get_db),
    adjustment_in: StockAdjustmentCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Créer un ajustement de stock.
    """
    # Vérifier que la pharmacie correspond
    if adjustment_in.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create adjustment for another pharmacy"
        )
    
    # Récupérer le produit
    product = db.query(Product).filter(
        Product.id == adjustment_in.product_id,
        Product.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Créer l'ajustement
    quantity_before = product.quantity
    quantity_after = quantity_before + adjustment_in.quantity_adjusted
    
    if quantity_after < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adjustment would result in negative stock"
        )
    
    adjustment = StockAdjustment(
        pharmacy_id=adjustment_in.pharmacy_id,
        product_id=adjustment_in.product_id,
        user_id=current_user.id,
        quantity_before=quantity_before,
        quantity_adjusted=adjustment_in.quantity_adjusted,
        quantity_after=quantity_after,
        reason=adjustment_in.reason,
        notes=adjustment_in.notes,
        is_approved=True,  # Auto-approuvé pour l'instant
        approved_by=current_user.id,
        approved_at=datetime.now(timezone.utc)
    )
    
    db.add(adjustment)
    
    # Mettre à jour le stock du produit
    product.quantity = quantity_after
    
    # Préparer les notes avec la raison de l'ajustement
    reason_labels = {
        "inventory": "Inventaire",
        "expiry": "Expiration",
        "damage": "Dommage",
        "loss": "Perte",
        "theft": "Vol",
        "error": "Erreur",
        "return_supplier": "Retour fournisseur",
        "other": "Autre"
    }
    reason_label = reason_labels.get(adjustment_in.reason.value, adjustment_in.reason.value)
    
    notes_text = f"Raison: {reason_label}"
    if adjustment_in.notes:
        notes_text += f" - {adjustment_in.notes}"
    
    # Créer un mouvement de stock
    movement = StockMovement(
        pharmacy_id=current_user.pharmacy_id,
        product_id=product.id,
        user_id=current_user.id,
        movement_type=MovementType.ADJUSTMENT,
        quantity=adjustment_in.quantity_adjusted,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        reference_type="adjustment",
        reference_id=None,  # Sera mis à jour après flush
        notes=notes_text
    )
    db.add(movement)
    db.flush()
    
    # Mettre à jour la référence du mouvement
    movement.reference_id = adjustment.id
    
    db.commit()
    db.refresh(adjustment)
    
    # Vérifier et créer des alertes de stock si nécessaire
    check_and_create_stock_alerts(db, product, current_user.pharmacy_id)
    db.commit()
    
    return adjustment


# ============ ALERTS ============

@router.get("/alerts", response_model=List[AlertSchema])
def get_alerts(
    skip: int = 0,
    limit: int = 100,
    is_read: Optional[bool] = None,
    is_resolved: Optional[bool] = None,
    alert_type: Optional[AlertType] = None,
    priority: Optional[AlertPriority] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Récupérer les alertes.
    """
    query = db.query(Alert).filter(
        Alert.pharmacy_id == current_user.pharmacy_id
    )
    
    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)
    
    if is_resolved is not None:
        query = query.filter(Alert.is_resolved == is_resolved)
    
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    
    if priority:
        query = query.filter(Alert.priority == priority)
    
    alerts = query.order_by(
        Alert.is_resolved.asc(),
        Alert.priority.desc(),
        desc(Alert.created_at)
    ).offset(skip).limit(limit).all()
    
    return alerts


@router.get("/alerts/stats", response_model=AlertStats)
def get_alert_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Statistiques d'alertes.
    """
    pharmacy_id = current_user.pharmacy_id
    
    # Total alertes
    total_alerts = db.query(Alert).filter(
        Alert.pharmacy_id == pharmacy_id
    ).count()
    
    # Alertes non lues
    unread_count = db.query(Alert).filter(
        Alert.pharmacy_id == pharmacy_id,
        Alert.is_read == False
    ).count()
    
    # Alertes non résolues
    unresolved_count = db.query(Alert).filter(
        Alert.pharmacy_id == pharmacy_id,
        Alert.is_resolved == False
    ).count()
    
    # Par type
    by_type = {}
    for alert_type in AlertType:
        count = db.query(Alert).filter(
            Alert.pharmacy_id == pharmacy_id,
            Alert.alert_type == alert_type,
            Alert.is_resolved == False
        ).count()
        by_type[alert_type.value] = count
    
    # Par priorité
    by_priority = {}
    for priority in AlertPriority:
        count = db.query(Alert).filter(
            Alert.pharmacy_id == pharmacy_id,
            Alert.priority == priority,
            Alert.is_resolved == False
        ).count()
        by_priority[priority.value] = count
    
    return AlertStats(
        total_alerts=total_alerts,
        unread_count=unread_count,
        unresolved_count=unresolved_count,
        by_type=by_type,
        by_priority=by_priority
    )


@router.put("/alerts/{alert_id}", response_model=AlertSchema)
def update_alert(
    *,
    db: Session = Depends(get_db),
    alert_id: int,
    alert_in: AlertUpdate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Mettre à jour une alerte (marquer comme lue/résolue).
    """
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    if alert_in.is_read is not None:
        alert.is_read = alert_in.is_read
    
    if alert_in.is_resolved is not None:
        alert.is_resolved = alert_in.is_resolved
        if alert_in.is_resolved:
            alert.resolved_at = datetime.now(timezone.utc)
            alert.resolved_by = current_user.id
    
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/alerts/generate", status_code=status.HTTP_201_CREATED)
def generate_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Générer automatiquement les alertes pour tous les produits.
    """
    pharmacy_id = current_user.pharmacy_id
    alerts_created = 0
    
    # Récupérer tous les produits actifs
    products = db.query(Product).filter(
        Product.pharmacy_id == pharmacy_id,
        Product.is_active == True
    ).all()
    
    for product in products:
        # Vérifier stock bas
        if product.quantity <= 0:
            if not _alert_exists(db, pharmacy_id, product.id, AlertType.OUT_OF_STOCK):
                _create_out_of_stock_alert(db, product, pharmacy_id)
                alerts_created += 1
        elif product.quantity <= product.min_quantity:
            if not _alert_exists(db, pharmacy_id, product.id, AlertType.LOW_STOCK):
                _create_low_stock_alert(db, product, pharmacy_id)
                alerts_created += 1
        
        # Vérifier expiration
        if product.expiry_date:
            days_until_expiry = (product.expiry_date - datetime.now(timezone.utc)).days
            
            if days_until_expiry < 0:
                if not _alert_exists(db, pharmacy_id, product.id, AlertType.EXPIRED):
                    _create_expired_alert(db, product, pharmacy_id)
                    alerts_created += 1
            elif days_until_expiry <= 30:
                if not _alert_exists(db, pharmacy_id, product.id, AlertType.EXPIRING_SOON):
                    _create_expiring_soon_alert(db, product, pharmacy_id, days_until_expiry)
                    alerts_created += 1
    
    db.commit()
    
    return {
        "message": f"{alerts_created} alerte(s) créée(s)",
        "alerts_created": alerts_created
    }


# ============ INVENTORIES ============

@router.get("/inventories", response_model=List[InventorySchema])
def get_inventories(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Récupérer les inventaires.
    """
    query = db.query(Inventory).filter(
        Inventory.pharmacy_id == current_user.pharmacy_id
    )
    
    if status:
        query = query.filter(Inventory.status == status)
    
    inventories = query.order_by(desc(Inventory.created_at)).offset(skip).limit(limit).all()
    return inventories


@router.post("/inventories", response_model=InventorySchema, status_code=status.HTTP_201_CREATED)
def create_inventory(
    *,
    db: Session = Depends(get_db),
    inventory_in: InventoryCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Créer un nouvel inventaire.
    """
    if inventory_in.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create inventory for another pharmacy"
        )
    
    # Générer un numéro d'inventaire unique
    inventory_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    # Créer l'inventaire
    inventory = Inventory(
        pharmacy_id=inventory_in.pharmacy_id,
        user_id=current_user.id,
        inventory_number=inventory_number,
        inventory_date=inventory_in.inventory_date,
        status="in_progress",
        notes=inventory_in.notes
    )
    
    db.add(inventory)
    db.flush()
    
    # Ajouter les items
    total_discrepancies = 0
    for item_data in inventory_in.items:
        product = db.query(Product).filter(
            Product.id == item_data.product_id,
            Product.pharmacy_id == current_user.pharmacy_id
        ).first()
        
        if not product:
            continue
        
        quantity_system = product.quantity
        quantity_counted = item_data.quantity_counted
        quantity_difference = quantity_counted - quantity_system
        
        if quantity_difference != 0:
            total_discrepancies += 1
        
        item = InventoryItem(
            inventory_id=inventory.id,
            product_id=item_data.product_id,
            quantity_system=quantity_system,
            quantity_counted=quantity_counted,
            quantity_difference=quantity_difference,
            notes=item_data.notes
        )
        db.add(item)
    
    inventory.total_products_counted = len(inventory_in.items)
    inventory.total_discrepancies = total_discrepancies
    
    db.commit()
    db.refresh(inventory)
    return inventory


@router.put("/inventories/{inventory_id}/complete", response_model=InventorySchema)
def complete_inventory(
    *,
    db: Session = Depends(get_db),
    inventory_id: int,
    apply_adjustments: bool = True,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Finaliser un inventaire et appliquer les ajustements au stock.
    """
    inventory = db.query(Inventory).filter(
        Inventory.id == inventory_id,
        Inventory.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory not found"
        )
    
    if inventory.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory is not in progress"
        )
    
    # Appliquer les ajustements si demandé
    if apply_adjustments:
        for item in inventory.items:
            if item.quantity_difference != 0:
                product = db.query(Product).filter(Product.id == item.product_id).first()
                if product:
                    # Créer l'ajustement
                    adjustment = StockAdjustment(
                        pharmacy_id=current_user.pharmacy_id,
                        product_id=product.id,
                        user_id=current_user.id,
                        quantity_before=product.quantity,
                        quantity_adjusted=item.quantity_difference,
                        quantity_after=item.quantity_counted,
                        reason=AdjustmentReason.INVENTORY,
                        notes=f"Ajustement suite à inventaire {inventory.inventory_number}",
                        is_approved=True,
                        approved_by=current_user.id,
                        approved_at=datetime.now(timezone.utc)
                    )
                    db.add(adjustment)
                    
                    # Mettre à jour le stock
                    product.quantity = item.quantity_counted
                    
                    # Créer mouvement de stock
                    movement = StockMovement(
                        pharmacy_id=current_user.pharmacy_id,
                        product_id=product.id,
                        user_id=current_user.id,
                        movement_type=MovementType.ADJUSTMENT,
                        quantity=item.quantity_difference,
                        quantity_before=item.quantity_system,
                        quantity_after=item.quantity_counted,
                        reference_type="inventory",
                        reference_id=inventory.id,
                        notes=f"Inventaire {inventory.inventory_number}"
                    )
                    db.add(movement)
    
    # Marquer l'inventaire comme terminé
    inventory.status = "completed"
    inventory.completed_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(inventory)
    return inventory


# ============ Helper Functions ============

def _alert_exists(db: Session, pharmacy_id: int, product_id: int, alert_type: AlertType) -> bool:
    """Vérifier si une alerte existe déjà pour ce produit."""
    return db.query(Alert).filter(
        Alert.pharmacy_id == pharmacy_id,
        Alert.product_id == product_id,
        Alert.alert_type == alert_type,
        Alert.is_resolved == False
    ).first() is not None


def _create_low_stock_alert(db: Session, product: Product, pharmacy_id: int):
    """Créer une alerte de stock bas."""
    alert = Alert(
        pharmacy_id=pharmacy_id,
        product_id=product.id,
        alert_type=AlertType.LOW_STOCK,
        priority=AlertPriority.MEDIUM,
        title=f"Stock bas: {product.name}",
        message=f"Le stock de {product.name} est faible ({product.quantity} unités). Seuil minimum: {product.min_quantity}"
    )
    db.add(alert)


def _create_out_of_stock_alert(db: Session, product: Product, pharmacy_id: int):
    """Créer une alerte de rupture de stock."""
    alert = Alert(
        pharmacy_id=pharmacy_id,
        product_id=product.id,
        alert_type=AlertType.OUT_OF_STOCK,
        priority=AlertPriority.HIGH,
        title=f"Rupture de stock: {product.name}",
        message=f"Le produit {product.name} est en rupture de stock."
    )
    db.add(alert)


def _create_expiring_soon_alert(db: Session, product: Product, pharmacy_id: int, days: int):
    """Créer une alerte d'expiration proche."""
    priority = AlertPriority.CRITICAL if days <= 7 else AlertPriority.HIGH if days <= 15 else AlertPriority.MEDIUM
    alert = Alert(
        pharmacy_id=pharmacy_id,
        product_id=product.id,
        alert_type=AlertType.EXPIRING_SOON,
        priority=priority,
        title=f"Expiration proche: {product.name}",
        message=f"Le produit {product.name} expire dans {days} jour(s)."
    )
    db.add(alert)


def _create_expired_alert(db: Session, product: Product, pharmacy_id: int):
    """Créer une alerte de produit expiré."""
    alert = Alert(
        pharmacy_id=pharmacy_id,
        product_id=product.id,
        alert_type=AlertType.EXPIRED,
        priority=AlertPriority.CRITICAL,
        title=f"Produit expiré: {product.name}",
        message=f"Le produit {product.name} est expiré depuis le {product.expiry_date.strftime('%d/%m/%Y')}."
    )
    db.add(alert)


def check_and_create_stock_alerts(db: Session, product: Product, pharmacy_id: int):
    """
    Vérifier le stock d'un produit et créer/résoudre les alertes appropriées.
    Cette fonction doit être appelée après chaque modification de stock.
    """
    # Résoudre les alertes de stock bas/rupture si le stock est maintenant au-dessus du minimum
    if product.quantity > product.min_quantity:
        # Résoudre les alertes de stock bas et rupture de stock
        existing_alerts = db.query(Alert).filter(
            Alert.pharmacy_id == pharmacy_id,
            Alert.product_id == product.id,
            Alert.alert_type.in_([AlertType.LOW_STOCK, AlertType.OUT_OF_STOCK]),
            Alert.is_resolved == False
        ).all()
        
        for alert in existing_alerts:
            alert.is_resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
    
    # Créer de nouvelles alertes si nécessaire
    if product.quantity <= 0:
        # Rupture de stock
        if not _alert_exists(db, pharmacy_id, product.id, AlertType.OUT_OF_STOCK):
            _create_out_of_stock_alert(db, product, pharmacy_id)
    elif product.quantity <= product.min_quantity:
        # Stock bas
        if not _alert_exists(db, pharmacy_id, product.id, AlertType.LOW_STOCK):
            _create_low_stock_alert(db, product, pharmacy_id)
    
    # Vérifier l'expiration
    if product.expiry_date:
        days_until_expiry = (product.expiry_date - datetime.now(timezone.utc)).days
        
        # Résoudre les alertes d'expiration si le produit n'est plus expiré ou n'expire plus bientôt
        if days_until_expiry > 30:
            existing_expiry_alerts = db.query(Alert).filter(
                Alert.pharmacy_id == pharmacy_id,
                Alert.product_id == product.id,
                Alert.alert_type.in_([AlertType.EXPIRING_SOON, AlertType.EXPIRED]),
                Alert.is_resolved == False
            ).all()
            
            for alert in existing_expiry_alerts:
                alert.is_resolved = True
                alert.resolved_at = datetime.now(timezone.utc)
        elif days_until_expiry < 0:
            # Produit expiré
            if not _alert_exists(db, pharmacy_id, product.id, AlertType.EXPIRED):
                _create_expired_alert(db, product, pharmacy_id)
        elif days_until_expiry <= 30:
            # Expire bientôt
            if not _alert_exists(db, pharmacy_id, product.id, AlertType.EXPIRING_SOON):
                _create_expiring_soon_alert(db, product, pharmacy_id, days_until_expiry)

