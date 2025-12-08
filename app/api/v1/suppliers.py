from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session, selectinload
from app.core.deps import get_current_pharmacy_user
from app.db.base import get_db
from app.models.user import User
from app.models.supplier import Supplier, SupplierOrder, SupplierOrderItem, OrderStatus
from app.models.product import Product
from app.models.stock import StockMovement, MovementType
from app.schemas.supplier import (
    Supplier as SupplierSchema,
    SupplierCreate,
    SupplierUpdate,
    SupplierOrder as SupplierOrderSchema,
    SupplierOrderCreate,
    SupplierOrderUpdate,
    ReceiveOrderRequest,
    ReturnItemRequest
)
import uuid

router = APIRouter()


# ============ SUPPLIER ORDERS (doit être AVANT /{supplier_id}) ============

@router.get("/orders", response_model=List[SupplierOrderSchema])
def read_orders(
    skip: int = 0,
    limit: int = 100,
    supplier_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste les commandes fournisseurs."""
    query = db.query(SupplierOrder).filter(
        SupplierOrder.pharmacy_id == current_user.pharmacy_id
    )
    
    if supplier_id:
        query = query.filter(SupplierOrder.supplier_id == supplier_id)
    
    orders = query.options(
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product),
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product_received),
        selectinload(SupplierOrder.supplier)
    ).order_by(SupplierOrder.created_at.desc()).offset(skip).limit(limit).all()
    return orders


@router.post("/orders", response_model=SupplierOrderSchema, status_code=status.HTTP_201_CREATED)
def create_order(
    *,
    db: Session = Depends(get_db),
    order_in: SupplierOrderCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Créer une nouvelle commande fournisseur."""
    if order_in.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create order for another pharmacy"
        )
    
    # Calculer les totaux
    subtotal = sum(item.unit_price * item.quantity_ordered for item in order_in.items)
    total_amount = subtotal + order_in.tax + order_in.shipping_cost
    
    # Générer un numéro de commande unique
    order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    # Créer la commande
    order = SupplierOrder(
        pharmacy_id=order_in.pharmacy_id,
        supplier_id=order_in.supplier_id,
        user_id=current_user.id,
        order_number=order_number,
        expected_delivery_date=order_in.expected_delivery_date,
        subtotal=subtotal,
        tax=order_in.tax,
        shipping_cost=order_in.shipping_cost,
        total_amount=total_amount,
        notes=order_in.notes
    )
    
    db.add(order)
    db.flush()
    
    # Créer les items
    for item_data in order_in.items:
        order_item = SupplierOrderItem(
            order_id=order.id,
            product_id=item_data.product_id,
            quantity_ordered=item_data.quantity_ordered,
            unit_price=item_data.unit_price,
            total=item_data.unit_price * item_data.quantity_ordered
        )
        db.add(order_item)
    
    db.commit()
    
    # Recharger l'ordre avec les relations pour la sérialisation
    db.refresh(order)
    order = db.query(SupplierOrder).options(
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product),
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product_received),
        selectinload(SupplierOrder.supplier)
    ).filter(SupplierOrder.id == order.id).first()
    
    return order


@router.get("/orders/{order_id}", response_model=SupplierOrderSchema)
def read_order(
    *,
    db: Session = Depends(get_db),
    order_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir une commande par ID."""
    order = db.query(SupplierOrder).options(
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product),
        selectinload(SupplierOrder.supplier)
    ).filter(
        SupplierOrder.id == order_id,
        SupplierOrder.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return order


@router.put("/orders/{order_id}/receive", response_model=SupplierOrderSchema)
def receive_order(
    *,
    db: Session = Depends(get_db),
    order_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Réceptionner une commande et mettre à jour le stock."""
    order = db.query(SupplierOrder).options(
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product),
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product_received),
        selectinload(SupplierOrder.supplier)
    ).filter(
        SupplierOrder.id == order_id,
        SupplierOrder.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status == OrderStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order already delivered"
        )
    
    # Mettre à jour le stock pour chaque item
    for item in order.items:
        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.pharmacy_id == current_user.pharmacy_id
        ).first()
        
        if product:
            # Enregistrer le stock avant mise à jour
            quantity_before = product.quantity
            
            # Mettre à jour le stock
            product.quantity += item.quantity_ordered
            
            # Créer un mouvement de stock
            stock_movement = StockMovement(
                pharmacy_id=current_user.pharmacy_id,
                product_id=item.product_id,
                user_id=current_user.id,
                movement_type=MovementType.PURCHASE,
                quantity=item.quantity_ordered,
                quantity_before=quantity_before,
                quantity_after=product.quantity,
                reference_type="supplier_order",
                reference_id=order.id,
                unit_cost=item.unit_price,
                notes=f"Réception commande {order.order_number}"
            )
            db.add(stock_movement)
            
            item.quantity_received = item.quantity_ordered
    
    order.delivery_date = datetime.utcnow()
    order.status = OrderStatus.DELIVERED
    
    db.commit()
    
    # Recharger l'ordre avec les relations pour la sérialisation
    order = db.query(SupplierOrder).options(
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product),
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product_received),
        selectinload(SupplierOrder.supplier)
    ).filter(SupplierOrder.id == order.id).first()
    
    return order


@router.put("/orders/{order_id}/receive-items", response_model=SupplierOrderSchema)
def receive_order_items(
    *,
    db: Session = Depends(get_db),
    order_id: int,
    receive_data: ReceiveOrderRequest,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Réceptionner une commande ligne par ligne avec possibilité de substitution."""
    order = db.query(SupplierOrder).options(
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product),
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product_received),
        selectinload(SupplierOrder.supplier)
    ).filter(
        SupplierOrder.id == order_id,
        SupplierOrder.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status == OrderStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order already delivered"
        )
    
    now = datetime.utcnow()
    
    # Traiter chaque item reçu
    for receive_item in receive_data.items:
        order_item = next((item for item in order.items if item.id == receive_item.item_id), None)
        
        if not order_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order item {receive_item.item_id} not found"
            )
        
        # Validation : si substitution, raison obligatoire
        if receive_item.product_received_id and receive_item.product_received_id != order_item.product_id:
            if not receive_item.substitution_reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Substitution reason required for item {receive_item.item_id}"
                )
        
        # Déterminer le produit à recevoir
        product_to_receive_id = receive_item.product_received_id or order_item.product_id
        
        # Vérifier que le produit existe
        product = db.query(Product).filter(
            Product.id == product_to_receive_id,
            Product.pharmacy_id == current_user.pharmacy_id
        ).first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {product_to_receive_id} not found"
            )
        
        # Enregistrer le stock avant mise à jour
        quantity_before = product.quantity
        
        # Mettre à jour le stock
        product.quantity += receive_item.quantity_received
        
        # Vérifier et créer des alertes de stock si nécessaire
        from app.api.v1.stock import check_and_create_stock_alerts
        check_and_create_stock_alerts(db, product, current_user.pharmacy_id)
        
        # Créer un mouvement de stock
        notes_text = f"Réception commande {order.order_number}"
        if receive_item.substitution_reason:
            notes_text += f" - Substitution: {receive_item.substitution_reason}"
        if receive_item.notes:
            notes_text += f" - {receive_item.notes}"
        
        stock_movement = StockMovement(
            pharmacy_id=current_user.pharmacy_id,
            product_id=product_to_receive_id,
            user_id=current_user.id,
            movement_type=MovementType.PURCHASE,
            quantity=receive_item.quantity_received,
            quantity_before=quantity_before,
            quantity_after=product.quantity,
            reference_type="supplier_order",
            reference_id=order.id,
            unit_cost=order_item.unit_price,
            notes=notes_text
        )
        db.add(stock_movement)
        
        # Mettre à jour l'item de commande
        order_item.quantity_received = receive_item.quantity_received
        order_item.product_received_id = product_to_receive_id if product_to_receive_id != order_item.product_id else None
        order_item.substitution_reason = receive_item.substitution_reason
        order_item.received_at = now
    
    # Vérifier si tous les items sont reçus
    all_received = all(
        item.quantity_received >= item.quantity_ordered 
        for item in order.items
    )
    
    if all_received:
        order.delivery_date = now
        order.status = OrderStatus.DELIVERED
    
    db.commit()
    
    # Recharger l'ordre avec les relations
    order = db.query(SupplierOrder).options(
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product),
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product_received),
        selectinload(SupplierOrder.supplier)
    ).filter(SupplierOrder.id == order.id).first()
    
    return order


@router.post("/orders/{order_id}/return-item", response_model=SupplierOrderSchema)
def return_order_item(
    *,
    db: Session = Depends(get_db),
    order_id: int,
    return_data: ReturnItemRequest,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Retourner un produit reçu par erreur."""
    order = db.query(SupplierOrder).options(
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product),
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product_received),
        selectinload(SupplierOrder.supplier)
    ).filter(
        SupplierOrder.id == order_id,
        SupplierOrder.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    order_item = next((item for item in order.items if item.id == return_data.item_id), None)
    
    if not order_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order item not found"
        )
    
    if return_data.return_quantity > order_item.quantity_received:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return quantity cannot exceed received quantity"
        )
    
    if return_data.return_quantity > (order_item.quantity_received - order_item.return_quantity):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return quantity exceeds available quantity to return"
        )
    
    # Déterminer le produit à retourner (celui reçu ou celui commandé)
    product_to_return_id = order_item.product_received_id or order_item.product_id
    
    product = db.query(Product).filter(
        Product.id == product_to_return_id,
        Product.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Vérifier que le stock est suffisant
    if product.quantity < return_data.return_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient stock to return"
        )
    
    # Enregistrer le stock avant mise à jour
    quantity_before = product.quantity
    
    # Retirer du stock
    product.quantity -= return_data.return_quantity
    
    # Vérifier et créer des alertes de stock si nécessaire
    from app.api.v1.stock import check_and_create_stock_alerts
    check_and_create_stock_alerts(db, product, current_user.pharmacy_id)
    
    # Créer un mouvement de stock pour le retour
    stock_movement = StockMovement(
        pharmacy_id=current_user.pharmacy_id,
        product_id=product_to_return_id,
        user_id=current_user.id,
        movement_type=MovementType.RETURN,
        quantity=-return_data.return_quantity,  # Négatif car c'est une sortie
        quantity_before=quantity_before,
        quantity_after=product.quantity,
        reference_type="supplier_order_return",
        reference_id=order.id,
        unit_cost=order_item.unit_price,
        notes=f"Retour commande {order.order_number} - {return_data.return_reason}"
    )
    db.add(stock_movement)
    
    # Mettre à jour l'item
    order_item.is_returned = True
    order_item.return_quantity += return_data.return_quantity
    order_item.return_reason = return_data.return_reason
    order_item.return_date = datetime.utcnow()
    
    db.commit()
    
    # Recharger l'ordre avec les relations
    order = db.query(SupplierOrder).options(
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product),
        selectinload(SupplierOrder.items).selectinload(SupplierOrderItem.product_received),
        selectinload(SupplierOrder.supplier)
    ).filter(SupplierOrder.id == order.id).first()
    
    return order


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    *,
    db: Session = Depends(get_db),
    order_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Response:
    """Supprimer une commande (seulement si pas encore livrée)."""
    order = db.query(SupplierOrder).filter(
        SupplierOrder.id == order_id,
        SupplierOrder.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status == OrderStatus.DELIVERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a delivered order"
        )
    
    db.delete(order)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============ SUPPLIERS ============

@router.get("/", response_model=List[SupplierSchema])
def read_suppliers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste les fournisseurs de la pharmacie."""
    query = db.query(Supplier).filter(
        Supplier.pharmacy_id == current_user.pharmacy_id
    )
    
    if search:
        query = query.filter(Supplier.name.ilike(f"%{search}%"))
    
    suppliers = query.offset(skip).limit(limit).all()
    return suppliers


@router.post("/", response_model=SupplierSchema, status_code=status.HTTP_201_CREATED)
def create_supplier(
    *,
    db: Session = Depends(get_db),
    supplier_in: SupplierCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Créer un nouveau fournisseur."""
    if supplier_in.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create supplier for another pharmacy"
        )
    
    supplier = Supplier(**supplier_in.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierSchema)
def read_supplier(
    *,
    db: Session = Depends(get_db),
    supplier_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir un fournisseur par ID."""
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    return supplier


@router.put("/{supplier_id}", response_model=SupplierSchema)
def update_supplier(
    *,
    db: Session = Depends(get_db),
    supplier_id: int,
    supplier_in: SupplierUpdate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Mettre à jour un fournisseur."""
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    update_data = supplier_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)
    
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    *,
    db: Session = Depends(get_db),
    supplier_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Response:
    """Supprimer un fournisseur."""
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found"
        )
    
    db.delete(supplier)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
