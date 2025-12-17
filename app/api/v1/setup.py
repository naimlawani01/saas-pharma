"""
Routes de configuration initiale et inscription.

Ces endpoints permettent :
- De configurer l'application lors de la première utilisation (local)
- De créer de nouveaux comptes (cloud)
"""

from typing import Any
from pydantic import BaseModel, EmailStr
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.base import get_db
from app.models.user import User
from app.models.pharmacy import Pharmacy
from app.schemas.user import User as UserSchema

router = APIRouter()


class SetupStatus(BaseModel):
    """Statut de la configuration initiale"""
    needs_setup: bool
    has_pharmacy: bool
    has_admin: bool
    message: str


# Types d'activité supportés
BUSINESS_TYPES = [
    "pharmacy",     # Pharmacie
    "grocery",      # Épicerie / Alimentation générale
    "hardware",     # Quincaillerie
    "cosmetics",    # Cosmétiques
    "auto_parts",   # Pièces auto
    "clothing",     # Vêtements / Mode
    "electronics",  # Électronique
    "restaurant",   # Restaurant / Alimentation
    "wholesale",    # Grossiste
    "general",      # Commerce général
]


class PharmacySetup(BaseModel):
    """Informations du commerce pour le setup"""
    name: str
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    email: str | None = None
    license_number: str | None = None
    business_type: str = "general"  # Type d'activité


class AdminSetup(BaseModel):
    """Informations de l'admin pour le setup"""
    email: EmailStr
    username: str
    password: str
    full_name: str | None = None


class InitialSetup(BaseModel):
    """Configuration initiale complète"""
    pharmacy: PharmacySetup
    admin: AdminSetup


class SetupResponse(BaseModel):
    """Réponse après le setup"""
    success: bool
    message: str
    pharmacy_id: int
    admin_email: str


@router.get(
    "/status",
    response_model=SetupStatus,
    summary="Vérifier si le setup initial est nécessaire",
)
def check_setup_status(
    db: Session = Depends(get_db),
) -> Any:
    """
    Vérifie si l'application nécessite une configuration initiale.
    
    Retourne:
    - needs_setup: True si aucun utilisateur n'existe
    - has_pharmacy: True si au moins une pharmacie existe
    - has_admin: True si au moins un admin existe
    """
    # Compter les utilisateurs
    user_count = db.query(User).count()
    pharmacy_count = db.query(Pharmacy).count()
    admin_count = db.query(User).filter(User.role == "admin").count()
    
    needs_setup = user_count == 0
    
    if needs_setup:
        message = "Configuration initiale requise. Veuillez créer votre compte administrateur."
    else:
        message = "L'application est déjà configurée."
    
    return SetupStatus(
        needs_setup=needs_setup,
        has_pharmacy=pharmacy_count > 0,
        has_admin=admin_count > 0,
        message=message,
    )


@router.post(
    "/initialize",
    response_model=SetupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Configuration initiale de l'application",
)
def initialize_app(
    *,
    db: Session = Depends(get_db),
    setup_data: InitialSetup,
) -> Any:
    """
    Configure l'application pour la première utilisation.
    
    Crée:
    1. La pharmacie avec les informations fournies
    2. Le compte administrateur
    
    ⚠️ Cet endpoint ne fonctionne que si aucun utilisateur n'existe.
    """
    # Vérifier qu'aucun utilisateur n'existe (sécurité)
    existing_users = db.query(User).count()
    if existing_users > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'application est déjà configurée. Le setup initial n'est plus disponible."
        )
    
    # Vérifier si l'email existe déjà
    existing_email = db.query(User).filter(User.email == setup_data.admin.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé."
        )
    
    # Vérifier si le username existe déjà
    existing_username = db.query(User).filter(User.username == setup_data.admin.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà utilisé."
        )
    
    # Valider le type d'activité
    business_type = setup_data.pharmacy.business_type
    if business_type not in BUSINESS_TYPES:
        business_type = "general"
    
    try:
        # 1. Créer le commerce
        pharmacy = Pharmacy(
            name=setup_data.pharmacy.name,
            address=setup_data.pharmacy.address,
            city=setup_data.pharmacy.city,
            phone=setup_data.pharmacy.phone,
            email=setup_data.pharmacy.email,
            license_number=setup_data.pharmacy.license_number,
            business_type=business_type,
            is_active=True,
        )
        db.add(pharmacy)
        db.commit()
        db.refresh(pharmacy)
        
        # 2. Créer l'administrateur
        admin = User(
            email=setup_data.admin.email,
            username=setup_data.admin.username,
            full_name=setup_data.admin.full_name or setup_data.admin.username,
            hashed_password=get_password_hash(setup_data.admin.password),
            role="admin",
            pharmacy_id=pharmacy.id,
            is_active=True,
            is_superuser=True,  # Premier admin est super admin
        )
        db.add(admin)
        db.commit()
        
        return SetupResponse(
            success=True,
            message="Configuration initiale réussie! Vous pouvez maintenant vous connecter.",
            pharmacy_id=pharmacy.id,
            admin_email=admin.email,
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la configuration: {str(e)}"
        )


# ============================================================
# INSCRIPTION PUBLIQUE (CLOUD)
# ============================================================

class RegisterRequest(BaseModel):
    """Demande d'inscription d'un nouveau commerce"""
    # Commerce
    pharmacy_name: str
    pharmacy_address: str | None = None
    pharmacy_city: str | None = None
    pharmacy_phone: str | None = None
    pharmacy_email: str | None = None
    pharmacy_license: str | None = None
    business_type: str = "general"  # Type d'activité
    # Admin
    admin_email: EmailStr
    admin_username: str
    admin_password: str
    admin_full_name: str | None = None


class RegisterResponse(BaseModel):
    """Réponse après inscription"""
    success: bool
    message: str
    pharmacy_id: int
    pharmacy_sync_id: str
    user_id: int
    user_sync_id: str
    admin_email: str


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inscription d'un nouveau commerce",
)
def register_pharmacy(
    *,
    db: Session = Depends(get_db),
    data: RegisterRequest,
) -> Any:
    """
    Inscription publique d'un nouveau commerce.
    
    Crée un nouveau commerce et un compte administrateur.
    Contrairement à /initialize, cet endpoint peut être appelé plusieurs fois
    pour créer de nouveaux commerces.
    
    Utilisé par l'app Electron lors du setup initial.
    """
    # Vérifier si l'email existe déjà
    existing_email = db.query(User).filter(User.email == data.admin_email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé. Avez-vous déjà un compte ?"
        )
    
    # Vérifier si le username existe déjà
    existing_username = db.query(User).filter(User.username == data.admin_username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà utilisé."
        )
    
    # Valider le type d'activité
    business_type = data.business_type
    if business_type not in BUSINESS_TYPES:
        business_type = "general"
    
    try:
        # Générer des sync_id uniques pour la synchronisation
        pharmacy_sync_id = str(uuid.uuid4())
        user_sync_id = str(uuid.uuid4())
        
        # 1. Créer le commerce
        pharmacy = Pharmacy(
            name=data.pharmacy_name,
            address=data.pharmacy_address,
            city=data.pharmacy_city,
            phone=data.pharmacy_phone,
            email=data.pharmacy_email,
            license_number=data.pharmacy_license,
            business_type=business_type,
            is_active=True,
            sync_id=pharmacy_sync_id,
        )
        db.add(pharmacy)
        db.commit()
        db.refresh(pharmacy)
        
        # 2. Créer l'administrateur
        admin = User(
            email=data.admin_email,
            username=data.admin_username,
            full_name=data.admin_full_name or data.admin_username,
            hashed_password=get_password_hash(data.admin_password),
            role="admin",
            pharmacy_id=pharmacy.id,
            is_active=True,
            is_superuser=False,  # Pas super admin, juste admin de sa pharmacie
            sync_id=user_sync_id,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        return RegisterResponse(
            success=True,
            message="Inscription réussie ! Votre compte a été créé.",
            pharmacy_id=pharmacy.id,
            pharmacy_sync_id=pharmacy_sync_id,
            user_id=admin.id,
            user_sync_id=user_sync_id,
            admin_email=admin.email,
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'inscription: {str(e)}"
        )

