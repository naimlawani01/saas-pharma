from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import get_current_active_user, get_current_superuser
from app.db.base import get_db
from app.models.user import User
from app.models.pharmacy import Pharmacy
from app.schemas.pharmacy import Pharmacy as PharmacySchema, PharmacyCreate, PharmacyUpdate

router = APIRouter()


@router.get("/", response_model=List[PharmacySchema])
def read_pharmacies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Liste toutes les pharmacies (admin seulement) ou la pharmacie de l'utilisateur."""
    if current_user.is_superuser:
        pharmacies = db.query(Pharmacy).offset(skip).limit(limit).all()
    else:
        if current_user.pharmacy_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pharmacy not found"
            )
        pharmacies = [db.query(Pharmacy).filter(Pharmacy.id == current_user.pharmacy_id).first()]
    
    return pharmacies


@router.post("/", response_model=PharmacySchema, status_code=status.HTTP_201_CREATED)
def create_pharmacy(
    *,
    db: Session = Depends(get_db),
    pharmacy_in: PharmacyCreate,
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """Créer une nouvelle pharmacie (admin seulement)."""
    pharmacy = Pharmacy(**pharmacy_in.model_dump())
    db.add(pharmacy)
    db.commit()
    db.refresh(pharmacy)
    return pharmacy


@router.get("/{pharmacy_id}", response_model=PharmacySchema)
def read_pharmacy(
    *,
    db: Session = Depends(get_db),
    pharmacy_id: int,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Obtenir une pharmacie par ID."""
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found"
        )
    
    # Vérifier les permissions
    if not current_user.is_superuser and current_user.pharmacy_id != pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return pharmacy


@router.put("/{pharmacy_id}", response_model=PharmacySchema)
def update_pharmacy(
    *,
    db: Session = Depends(get_db),
    pharmacy_id: int,
    pharmacy_in: PharmacyUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Mettre à jour une pharmacie."""
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacy not found"
        )
    
    # Vérifier les permissions
    if not current_user.is_superuser and current_user.pharmacy_id != pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    update_data = pharmacy_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pharmacy, field, value)
    
    db.commit()
    db.refresh(pharmacy)
    return pharmacy
