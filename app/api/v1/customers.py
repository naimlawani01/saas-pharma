from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.core.deps import get_current_pharmacy_user
from app.db.base import get_db
from app.models.user import User
from app.models.customer import Customer
from app.schemas.customer import Customer as CustomerSchema, CustomerCreate, CustomerUpdate

router = APIRouter()


@router.get("/", response_model=List[CustomerSchema])
def read_customers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Liste les clients de la pharmacie."""
    query = db.query(Customer).filter(Customer.pharmacy_id == current_user.pharmacy_id)
    
    if search:
        query = query.filter(
            (Customer.first_name.ilike(f"%{search}%")) |
            (Customer.last_name.ilike(f"%{search}%")) |
            (Customer.phone.ilike(f"%{search}%")) |
            (Customer.email.ilike(f"%{search}%"))
        )
    
    customers = query.offset(skip).limit(limit).all()
    return customers


@router.post("/", response_model=CustomerSchema, status_code=status.HTTP_201_CREATED)
def create_customer(
    *,
    db: Session = Depends(get_db),
    customer_in: CustomerCreate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Créer un nouveau client."""
    # Vérifier que la pharmacie correspond
    if customer_in.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create customer for another pharmacy"
        )
    
    customer = Customer(**customer_in.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerSchema)
def read_customer(
    *,
    db: Session = Depends(get_db),
    customer_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Obtenir un client par ID."""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    return customer


@router.put("/{customer_id}", response_model=CustomerSchema)
def update_customer(
    *,
    db: Session = Depends(get_db),
    customer_id: int,
    customer_in: CustomerUpdate,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Any:
    """Mettre à jour un client."""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    update_data = customer_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}")
def delete_customer(
    *,
    db: Session = Depends(get_db),
    customer_id: int,
    current_user: User = Depends(get_current_pharmacy_user)
) -> Response:
    """Supprimer un client."""
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.pharmacy_id == current_user.pharmacy_id
    ).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    db.delete(customer)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
