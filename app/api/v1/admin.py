"""
Endpoints pour le Super Admin - Gestion globale du système.
Accessible uniquement aux utilisateurs avec is_superuser=True.
"""
from typing import Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr

from app.core.deps import get_current_superuser, get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.pharmacy import Pharmacy
from app.models.product import Product
from app.models.sale import Sale
from app.models.customer import Customer
from app.schemas.pharmacy import Pharmacy as PharmacySchema, PharmacyCreate, PharmacyUpdate
from app.schemas.user import User as UserSchema

router = APIRouter()


# ============ SCHEMAS ============

class PharmacyWithStats(PharmacySchema):
    """Pharmacie avec statistiques."""
    users_count: int = 0
    products_count: int = 0
    customers_count: int = 0
    total_sales: float = 0
    sales_count: int = 0


class PharmacyOnboarding(BaseModel):
    """Données pour créer une pharmacie avec son admin."""
    # Pharmacie
    pharmacy_name: str
    pharmacy_address: Optional[str] = None
    pharmacy_city: Optional[str] = None
    pharmacy_phone: Optional[str] = None
    pharmacy_email: Optional[str] = None
    license_number: Optional[str] = None
    
    # Admin de la pharmacie
    admin_email: EmailStr
    admin_username: str
    admin_password: str
    admin_full_name: Optional[str] = None


class DashboardStats(BaseModel):
    """Statistiques globales pour le super admin."""
    total_pharmacies: int
    active_pharmacies: int
    total_users: int
    total_products: int
    total_sales: float
    total_customers: int
    pharmacies_this_month: int
    sales_this_month: float


class UserWithPharmacy(UserSchema):
    """Utilisateur avec info pharmacie."""
    pharmacy_name: Optional[str] = None


# ============ DASHBOARD ============

@router.get("/dashboard", response_model=DashboardStats, summary="Dashboard Super Admin")
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Statistiques globales du système pour le super admin.
    """
    # Ce mois-ci
    today = datetime.utcnow()
    first_day_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Pharmacies
    total_pharmacies = db.query(Pharmacy).count()
    active_pharmacies = db.query(Pharmacy).filter(Pharmacy.is_active == True).count()
    pharmacies_this_month = db.query(Pharmacy).filter(
        Pharmacy.created_at >= first_day_of_month
    ).count()
    
    # Utilisateurs
    total_users = db.query(User).count()
    
    # Produits
    total_products = db.query(Product).count()
    
    # Clients
    total_customers = db.query(Customer).count()
    
    # Ventes
    total_sales = db.query(func.sum(Sale.final_amount)).scalar() or 0
    sales_this_month = db.query(func.sum(Sale.final_amount)).filter(
        Sale.created_at >= first_day_of_month
    ).scalar() or 0
    
    return DashboardStats(
        total_pharmacies=total_pharmacies,
        active_pharmacies=active_pharmacies,
        total_users=total_users,
        total_products=total_products,
        total_sales=round(total_sales, 2),
        total_customers=total_customers,
        pharmacies_this_month=pharmacies_this_month,
        sales_this_month=round(sales_this_month, 2),
    )


# ============ PHARMACIES ============

@router.get("/pharmacies", response_model=List[PharmacyWithStats], summary="Liste des pharmacies")
def list_pharmacies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Any:
    """
    Liste toutes les pharmacies avec leurs statistiques.
    """
    query = db.query(Pharmacy)
    
    if search:
        query = query.filter(
            Pharmacy.name.ilike(f"%{search}%") |
            Pharmacy.city.ilike(f"%{search}%")
        )
    
    if is_active is not None:
        query = query.filter(Pharmacy.is_active == is_active)
    
    pharmacies = query.order_by(Pharmacy.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for pharmacy in pharmacies:
        # Compter les statistiques
        users_count = db.query(User).filter(User.pharmacy_id == pharmacy.id).count()
        products_count = db.query(Product).filter(Product.pharmacy_id == pharmacy.id).count()
        customers_count = db.query(Customer).filter(Customer.pharmacy_id == pharmacy.id).count()
        sales_count = db.query(Sale).filter(Sale.pharmacy_id == pharmacy.id).count()
        total_sales = db.query(func.sum(Sale.final_amount)).filter(
            Sale.pharmacy_id == pharmacy.id
        ).scalar() or 0
        
        pharmacy_dict = {
            **pharmacy.__dict__,
            "users_count": users_count,
            "products_count": products_count,
            "customers_count": customers_count,
            "sales_count": sales_count,
            "total_sales": round(total_sales, 2),
        }
        result.append(PharmacyWithStats(**pharmacy_dict))
    
    return result


@router.post("/pharmacies", response_model=PharmacySchema, status_code=status.HTTP_201_CREATED, summary="Créer une pharmacie")
def create_pharmacy(
    pharmacy_in: PharmacyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Créer une nouvelle pharmacie.
    """
    # Vérifier l'unicité du numéro de licence
    if pharmacy_in.license_number:
        existing = db.query(Pharmacy).filter(
            Pharmacy.license_number == pharmacy_in.license_number
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce numéro de licence existe déjà"
            )
    
    pharmacy = Pharmacy(**pharmacy_in.model_dump())
    db.add(pharmacy)
    db.commit()
    db.refresh(pharmacy)
    return pharmacy


@router.post("/pharmacies/onboarding", response_model=PharmacyWithStats, status_code=status.HTTP_201_CREATED, summary="Onboarding complet")
def onboard_pharmacy(
    data: PharmacyOnboarding,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Créer une pharmacie avec son administrateur en une seule opération.
    """
    # Vérifier l'unicité de l'email
    if db.query(User).filter(User.email == data.admin_email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé"
        )
    
    # Vérifier l'unicité du username
    if db.query(User).filter(User.username == data.admin_username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà utilisé"
        )
    
    # Vérifier l'unicité du numéro de licence
    if data.license_number:
        if db.query(Pharmacy).filter(Pharmacy.license_number == data.license_number).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce numéro de licence existe déjà"
            )
    
    # Créer la pharmacie
    pharmacy = Pharmacy(
        name=data.pharmacy_name,
        address=data.pharmacy_address,
        city=data.pharmacy_city,
        phone=data.pharmacy_phone,
        email=data.pharmacy_email,
        license_number=data.license_number,
    )
    db.add(pharmacy)
    db.flush()  # Pour obtenir l'ID
    
    # Créer l'admin de la pharmacie
    admin_user = User(
        email=data.admin_email,
        username=data.admin_username,
        hashed_password=get_password_hash(data.admin_password),
        full_name=data.admin_full_name or data.admin_username,
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=False,
        pharmacy_id=pharmacy.id,
    )
    db.add(admin_user)
    
    db.commit()
    db.refresh(pharmacy)
    
    return PharmacyWithStats(
        **pharmacy.__dict__,
        users_count=1,
        products_count=0,
        customers_count=0,
        sales_count=0,
        total_sales=0,
    )


@router.get("/pharmacies/{pharmacy_id}", response_model=PharmacyWithStats, summary="Détail d'une pharmacie")
def get_pharmacy(
    pharmacy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Obtenir les détails d'une pharmacie avec ses statistiques.
    """
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacie non trouvée"
        )
    
    users_count = db.query(User).filter(User.pharmacy_id == pharmacy.id).count()
    products_count = db.query(Product).filter(Product.pharmacy_id == pharmacy.id).count()
    customers_count = db.query(Customer).filter(Customer.pharmacy_id == pharmacy.id).count()
    sales_count = db.query(Sale).filter(Sale.pharmacy_id == pharmacy.id).count()
    total_sales = db.query(func.sum(Sale.final_amount)).filter(
        Sale.pharmacy_id == pharmacy.id
    ).scalar() or 0
    
    return PharmacyWithStats(
        **pharmacy.__dict__,
        users_count=users_count,
        products_count=products_count,
        customers_count=customers_count,
        sales_count=sales_count,
        total_sales=round(total_sales, 2),
    )


@router.put("/pharmacies/{pharmacy_id}", response_model=PharmacySchema, summary="Modifier une pharmacie")
def update_pharmacy(
    pharmacy_id: int,
    pharmacy_in: PharmacyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Modifier une pharmacie.
    """
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacie non trouvée"
        )
    
    update_data = pharmacy_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pharmacy, field, value)
    
    db.commit()
    db.refresh(pharmacy)
    return pharmacy


@router.patch("/pharmacies/{pharmacy_id}/toggle", response_model=PharmacySchema, summary="Activer/Désactiver")
def toggle_pharmacy(
    pharmacy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Activer ou désactiver une pharmacie.
    """
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacie non trouvée"
        )
    
    pharmacy.is_active = not pharmacy.is_active
    db.commit()
    db.refresh(pharmacy)
    return pharmacy


@router.delete("/pharmacies/{pharmacy_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer une pharmacie")
def delete_pharmacy(
    pharmacy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Response:
    """
    Supprimer une pharmacie et toutes ses données.
    ATTENTION: Action irréversible !
    """
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacie non trouvée"
        )
    
    # Supprimer les utilisateurs associés
    db.query(User).filter(User.pharmacy_id == pharmacy_id).delete()
    
    # Supprimer la pharmacie (cascade supprimera produits, ventes, etc.)
    db.delete(pharmacy)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============ UTILISATEURS ============

@router.get("/pharmacies/{pharmacy_id}/users", response_model=List[UserSchema], summary="Utilisateurs d'une pharmacie")
def get_pharmacy_users(
    pharmacy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Liste les utilisateurs d'une pharmacie.
    """
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacie non trouvée"
        )
    
    users = db.query(User).filter(User.pharmacy_id == pharmacy_id).all()
    return users


@router.get("/users", response_model=List[UserWithPharmacy], summary="Tous les utilisateurs")
def list_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
) -> Any:
    """
    Liste tous les utilisateurs du système.
    """
    query = db.query(User)
    
    if search:
        query = query.filter(
            User.full_name.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%") |
            User.username.ilike(f"%{search}%")
        )
    
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        pharmacy_name = None
        if user.pharmacy_id:
            pharmacy = db.query(Pharmacy).filter(Pharmacy.id == user.pharmacy_id).first()
            if pharmacy:
                pharmacy_name = pharmacy.name
        
        result.append(UserWithPharmacy(
            **{k: v for k, v in user.__dict__.items() if not k.startswith('_')},
            pharmacy_name=pharmacy_name
        ))
    
    return result

