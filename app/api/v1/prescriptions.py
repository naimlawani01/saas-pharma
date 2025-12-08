from typing import Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, and_
from app.core.deps import get_current_pharmacy_user
from app.db.base import get_db
from app.models.user import User
from app.models.prescription import Prescription, PrescriptionItem, PrescriptionStatus
from app.models.customer import Customer
from app.models.product import Product
from app.schemas.prescription import (
    Prescription as PrescriptionSchema,
    PrescriptionCreate,
    PrescriptionUpdate,
)
import uuid

router = APIRouter()


def generate_prescription_number(pharmacy_id: int) -> str:
    """Génère un numéro unique de prescription."""
    date_str = datetime.now().strftime("%Y%m%d")
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"RX-{pharmacy_id}-{date_str}-{unique_id}"


@router.get("/", response_model=List[PrescriptionSchema])
def read_prescriptions(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    customer_id: Optional[int] = None,
    status_filter: Optional[PrescriptionStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste les prescriptions de la pharmacie."""
    query = db.query(Prescription).filter(
        Prescription.pharmacy_id == current_user.pharmacy_id
    )
    
    if search:
        query = query.filter(
            or_(
                Prescription.prescription_number.ilike(f"%{search}%"),
                Prescription.doctor_name.ilike(f"%{search}%"),
                Prescription.doctor_license_number.ilike(f"%{search}%"),
                Prescription.diagnosis.ilike(f"%{search}%"),
            )
        )
    
    if customer_id:
        query = query.filter(Prescription.customer_id == customer_id)
    
    if status_filter:
        query = query.filter(Prescription.status == status_filter)
    
    if start_date:
        query = query.filter(Prescription.prescription_date >= start_date)
    
    if end_date:
        query = query.filter(Prescription.prescription_date <= end_date)
    
    prescriptions = query.options(
        selectinload(Prescription.items).selectinload(PrescriptionItem.product),
        selectinload(Prescription.customer)
    ).order_by(Prescription.prescription_date.desc()).offset(skip).limit(limit).all()
    
    return prescriptions


@router.post("/", response_model=PrescriptionSchema, status_code=status.HTTP_201_CREATED)
def create_prescription(
    *,
    db: Session = Depends(get_db),
    prescription_in: PrescriptionCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Créer une nouvelle prescription."""
    # Vérifier que la pharmacie correspond
    if prescription_in.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create prescription for another pharmacy"
        )
    
    # Vérifier que le client existe
    customer = db.query(Customer).filter(
        Customer.id == prescription_in.customer_id,
        Customer.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Vérifier que tous les produits existent
    product_ids = [item.product_id for item in prescription_in.items]
    products = db.query(Product).filter(
        Product.id.in_(product_ids),
        Product.pharmacy_id == current_user.pharmacy_id
    ).all()
    
    if len(products) != len(product_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more products not found"
        )
    
    # Générer le numéro de prescription
    prescription_number = generate_prescription_number(current_user.pharmacy_id)
    
    # Créer la prescription
    prescription_data = prescription_in.model_dump(exclude={"items"})
    prescription_data["prescription_number"] = prescription_number
    prescription_data["user_id"] = current_user.id
    
    prescription = Prescription(**prescription_data)
    db.add(prescription)
    db.flush()  # Pour obtenir l'ID
    
    # Créer les items de prescription
    for item_data in prescription_in.items:
        prescription_item = PrescriptionItem(
            prescription_id=prescription.id,
            **item_data.model_dump()
        )
        db.add(prescription_item)
    
    db.commit()
    db.refresh(prescription)
    
    # Recharger avec les relations
    prescription = db.query(Prescription).options(
        selectinload(Prescription.items).selectinload(PrescriptionItem.product),
        selectinload(Prescription.customer)
    ).filter(Prescription.id == prescription.id).first()
    
    return prescription


@router.get("/{prescription_id}", response_model=PrescriptionSchema)
def read_prescription(
    *,
    db: Session = Depends(get_db),
    prescription_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir une prescription par ID."""
    prescription = db.query(Prescription).options(
        selectinload(Prescription.items).selectinload(PrescriptionItem.product),
        selectinload(Prescription.customer)
    ).filter(
        Prescription.id == prescription_id,
        Prescription.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
    
    return prescription


@router.put("/{prescription_id}", response_model=PrescriptionSchema)
def update_prescription(
    *,
    db: Session = Depends(get_db),
    prescription_id: int,
    prescription_in: PrescriptionUpdate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Mettre à jour une prescription."""
    prescription = db.query(Prescription).filter(
        Prescription.id == prescription_id,
        Prescription.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
    
    # Ne pas permettre la modification si la prescription est utilisée ou expirée
    if prescription.status in [PrescriptionStatus.USED, PrescriptionStatus.EXPIRED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a used or expired prescription"
        )
    
    update_data = prescription_in.model_dump(exclude_unset=True)
    
    # Vérifier la date d'expiration
    if "expiry_date" in update_data and update_data["expiry_date"]:
        if update_data["expiry_date"] < datetime.now(timezone.utc):
            update_data["status"] = PrescriptionStatus.EXPIRED
    
    for field, value in update_data.items():
        setattr(prescription, field, value)
    
    db.commit()
    db.refresh(prescription)
    
    # Recharger avec les relations
    prescription = db.query(Prescription).options(
        selectinload(Prescription.items).selectinload(PrescriptionItem.product),
        selectinload(Prescription.customer)
    ).filter(Prescription.id == prescription.id).first()
    
    return prescription


@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription(
    *,
    db: Session = Depends(get_db),
    prescription_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Response:
    """Supprimer une prescription."""
    prescription = db.query(Prescription).filter(
        Prescription.id == prescription_id,
        Prescription.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
    
    # Ne pas permettre la suppression si la prescription est utilisée
    if prescription.status == PrescriptionStatus.USED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a used prescription"
        )
    
    db.delete(prescription)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/customer/{customer_id}", response_model=List[PrescriptionSchema])
def read_customer_prescriptions(
    *,
    db: Session = Depends(get_db),
    customer_id: int,
    status_filter: Optional[PrescriptionStatus] = None,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir toutes les prescriptions d'un client."""
    # Vérifier que le client existe et appartient à la pharmacie
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    query = db.query(Prescription).filter(
        Prescription.customer_id == customer_id,
        Prescription.pharmacy_id == current_user.pharmacy_id
    )
    
    if status_filter:
        query = query.filter(Prescription.status == status_filter)
    
    prescriptions = query.options(
        selectinload(Prescription.items).selectinload(PrescriptionItem.product),
        selectinload(Prescription.customer)
    ).order_by(Prescription.prescription_date.desc()).all()
    
    return prescriptions


@router.post("/{prescription_id}/use", response_model=PrescriptionSchema)
def use_prescription(
    *,
    db: Session = Depends(get_db),
    prescription_id: int,
    items_used: List[dict],  # [{"item_id": 1, "quantity": 2}, ...]
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """
    Marquer des produits d'une prescription comme utilisés (lors d'une vente).
    
    items_used: Liste de dict avec item_id et quantity utilisée
    """
    prescription = db.query(Prescription).options(
        selectinload(Prescription.items)
    ).filter(
        Prescription.id == prescription_id,
        Prescription.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found"
        )
    
    if prescription.status in [PrescriptionStatus.USED, PrescriptionStatus.EXPIRED, PrescriptionStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot use a {prescription.status.value} prescription"
        )
    
    # Vérifier la date d'expiration
    if prescription.expiry_date and prescription.expiry_date < datetime.now(timezone.utc):
        prescription.status = PrescriptionStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prescription has expired"
        )
    
    # Mettre à jour les quantités utilisées
    for item_used in items_used:
        item_id = item_used.get("item_id")
        quantity = item_used.get("quantity", 0)
        
        prescription_item = next(
            (item for item in prescription.items if item.id == item_id),
            None
        )
        
        if not prescription_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prescription item {item_id} not found"
            )
        
        new_quantity_used = prescription_item.quantity_used + quantity
        
        if new_quantity_used > prescription_item.quantity_prescribed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quantity used ({new_quantity_used}) exceeds prescribed quantity ({prescription_item.quantity_prescribed})"
            )
        
        prescription_item.quantity_used = new_quantity_used
    
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
    db.refresh(prescription)
    
    # Recharger avec les relations
    prescription = db.query(Prescription).options(
        selectinload(Prescription.items).selectinload(PrescriptionItem.product),
        selectinload(Prescription.customer)
    ).filter(Prescription.id == prescription.id).first()
    
    return prescription

