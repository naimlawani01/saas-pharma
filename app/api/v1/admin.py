"""
Endpoints pour le Super Admin - Gestion globale du système.
Accessible uniquement aux utilisateurs avec is_superuser=True.
"""
from typing import Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, EmailStr
import pandas as pd
import io

from app.core.deps import get_current_superuser, get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.pharmacy import Pharmacy
from app.models.product import Product, ProductUnit
from app.models.sale import Sale
from app.models.customer import Customer
from app.models.license import License, LicenseActivation
from app.schemas.pharmacy import Pharmacy as PharmacySchema, PharmacyCreate, PharmacyUpdate
from app.schemas.user import User as UserSchema
from app.schemas.license import LicenseCreate, LicenseUpdate, LicenseResponse, LicenseActivationResponse

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
    """Données pour créer un commerce avec son admin."""
    # Commerce
    pharmacy_name: str
    pharmacy_address: Optional[str] = None
    pharmacy_city: Optional[str] = None
    pharmacy_phone: Optional[str] = None
    pharmacy_email: Optional[str] = None
    license_number: Optional[str] = None
    business_type: str = "general"  # Type d'activité
    
    # Admin du commerce
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
    business_type: Optional[str] = None,
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
    
    if business_type:
        query = query.filter(Pharmacy.business_type == business_type)
    
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
    Créer un commerce avec son administrateur en une seule opération.
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
    
    # Valider le type d'activité
    valid_business_types = ["pharmacy", "grocery", "hardware", "cosmetics", "auto_parts", "clothing", "electronics", "restaurant", "wholesale", "general"]
    business_type = data.business_type if data.business_type in valid_business_types else "general"
    
    # Créer le commerce
    pharmacy = Pharmacy(
        name=data.pharmacy_name,
        address=data.pharmacy_address,
        city=data.pharmacy_city,
        phone=data.pharmacy_phone,
        email=data.pharmacy_email,
        license_number=data.license_number,
        business_type=business_type,
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
    
    products_count = db.query(Product).filter(Product.pharmacy_id == pharmacy.id).count()
    
    return PharmacyWithStats(
        **pharmacy.__dict__,
        users_count=1,
        products_count=products_count,
        customers_count=0,
        sales_count=0,
        total_sales=0,
    )


@router.post("/pharmacies/{pharmacy_id}/products/import", summary="Importer des produits depuis Excel/CSV")
def import_products(
    pharmacy_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Importer des produits depuis un fichier Excel (.xlsx, .xls) ou CSV.
    
    Colonnes attendues (optionnelles sauf nom, prix_achat, prix_vente):
    - nom (requis)
    - description
    - code_barres / barcode
    - sku / reference
    - quantite / quantity (défaut: 0)
    - quantite_min / min_quantity (défaut: 0)
    - unite / unit (défaut: unit) - valeurs: unit, box, bottle, pack, tube, can, roll
    - prix_achat / purchase_price (requis)
    - prix_vente / selling_price (requis)
    - date_fabrication / manufacturing_date (format: YYYY-MM-DD)
    - date_expiration / expiry_date (format: YYYY-MM-DD)
    - ordonnance_requise / is_prescription_required (défaut: false)
    """
    # Vérifier que la pharmacie existe
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacie non trouvée"
        )
    
    # Vérifier le type de fichier
    file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
    if file_extension not in ['xlsx', 'xls', 'csv']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format de fichier non supporté. Utilisez .xlsx, .xls ou .csv"
        )
    
    try:
        # Lire le fichier
        contents = file.file.read()
        
        # Parser selon le type
        if file_extension == 'csv':
            df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
        else:  # Excel
            df = pd.read_excel(io.BytesIO(contents))
        
        # Normaliser les noms de colonnes (minuscules, sans accents, espaces remplacés par _)
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_').str.replace('é', 'e').str.replace('è', 'e')
        
        # Mapping des colonnes possibles
        column_mapping = {
            'nom': 'name',
            'name': 'name',
            'description': 'description',
            'code_barres': 'barcode',
            'barcode': 'barcode',
            'sku': 'sku',
            'reference': 'sku',
            'quantite': 'quantity',
            'quantity': 'quantity',
            'quantite_min': 'min_quantity',
            'min_quantity': 'min_quantity',
            'unite': 'unit',
            'unit': 'unit',
            'prix_achat': 'purchase_price',
            'purchase_price': 'purchase_price',
            'prix_vente': 'selling_price',
            'selling_price': 'selling_price',
            'date_fabrication': 'manufacturing_date',
            'manufacturing_date': 'manufacturing_date',
            'date_expiration': 'expiry_date',
            'expiry_date': 'expiry_date',
            'ordonnance_requise': 'is_prescription_required',
            'is_prescription_required': 'is_prescription_required',
        }
        
        # Renommer les colonnes
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # Vérifier les colonnes requises
        if 'name' not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Colonne 'nom' ou 'name' requise"
            )
        if 'purchase_price' not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Colonne 'prix_achat' ou 'purchase_price' requise"
            )
        if 'selling_price' not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Colonne 'prix_vente' ou 'selling_price' requise"
            )
        
        # Traiter chaque ligne
        created_count = 0
        error_count = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Valeurs par défaut
                name = str(row['name']).strip()
                if not name or name == 'nan':
                    continue
                
                # Convertir les valeurs
                purchase_price = float(row['purchase_price']) if pd.notna(row['purchase_price']) else 0
                selling_price = float(row['selling_price']) if pd.notna(row['selling_price']) else 0
                quantity = int(row.get('quantity', 0)) if pd.notna(row.get('quantity', 0)) else 0
                min_quantity = int(row.get('min_quantity', 0)) if pd.notna(row.get('min_quantity', 0)) else 0
                
                # Unité
                unit_str = str(row.get('unit', 'unit')).lower().strip() if pd.notna(row.get('unit')) else 'unit'
                try:
                    unit = ProductUnit(unit_str)
                except ValueError:
                    unit = ProductUnit.UNIT
                
                # Dates
                manufacturing_date = None
                if 'manufacturing_date' in row and pd.notna(row['manufacturing_date']):
                    try:
                        manufacturing_date = pd.to_datetime(row['manufacturing_date']).to_pydatetime()
                    except:
                        pass
                
                expiry_date = None
                if 'expiry_date' in row and pd.notna(row['expiry_date']):
                    try:
                        expiry_date = pd.to_datetime(row['expiry_date']).to_pydatetime()
                    except:
                        pass
                
                # Booléen
                is_prescription_required = False
                if 'is_prescription_required' in row and pd.notna(row['is_prescription_required']):
                    val = str(row['is_prescription_required']).lower().strip()
                    is_prescription_required = val in ['true', '1', 'oui', 'yes', 'o']
                
                # Créer le produit
                product = Product(
                    pharmacy_id=pharmacy_id,
                    name=name,
                    description=str(row.get('description', '')) if pd.notna(row.get('description')) else None,
                    barcode=str(row.get('barcode', '')).strip() if pd.notna(row.get('barcode')) else None,
                    sku=str(row.get('sku', '')).strip() if pd.notna(row.get('sku')) else None,
                    quantity=quantity,
                    min_quantity=min_quantity,
                    unit=unit,
                    purchase_price=purchase_price,
                    selling_price=selling_price,
                    manufacturing_date=manufacturing_date,
                    expiry_date=expiry_date,
                    is_prescription_required=is_prescription_required,
                    is_active=True,
                )
                
                db.add(product)
                created_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"Ligne {idx + 2}: {str(e)}")
                continue
        
        db.commit()
        
        return {
            "success": True,
            "created": created_count,
            "errors": error_count,
            "error_details": errors[:10],  # Limiter à 10 erreurs
            "message": f"{created_count} produit(s) importé(s) avec succès"
        }
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de l'import: {str(e)}"
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


@router.post("/pharmacies/{pharmacy_id}/products/import", summary="Importer des produits depuis Excel/CSV")
def import_products(
    pharmacy_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Importer des produits depuis un fichier Excel (.xlsx, .xls) ou CSV.
    
    Colonnes attendues (optionnelles sauf nom, prix_achat, prix_vente):
    - nom (requis)
    - description
    - code_barres / barcode
    - sku / reference
    - quantite / quantity (défaut: 0)
    - quantite_min / min_quantity (défaut: 0)
    - unite / unit (défaut: unit) - valeurs: unit, box, bottle, pack, tube, can, roll
    - prix_achat / purchase_price (requis)
    - prix_vente / selling_price (requis)
    - date_fabrication / manufacturing_date (format: YYYY-MM-DD)
    - date_expiration / expiry_date (format: YYYY-MM-DD)
    - ordonnance_requise / is_prescription_required (défaut: false)
    """
    # Vérifier que la pharmacie existe
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacie non trouvée"
        )
    
    # Vérifier le type de fichier
    file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
    if file_extension not in ['xlsx', 'xls', 'csv']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format de fichier non supporté. Utilisez .xlsx, .xls ou .csv"
        )
    
    try:
        # Lire le fichier
        contents = file.file.read()
        
        # Parser selon le type
        if file_extension == 'csv':
            df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
        else:  # Excel
            df = pd.read_excel(io.BytesIO(contents))
        
        # Normaliser les noms de colonnes (minuscules, sans accents, espaces remplacés par _)
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_').str.replace('é', 'e').str.replace('è', 'e')
        
        # Mapping des colonnes possibles
        column_mapping = {
            'nom': 'name',
            'name': 'name',
            'description': 'description',
            'code_barres': 'barcode',
            'barcode': 'barcode',
            'sku': 'sku',
            'reference': 'sku',
            'quantite': 'quantity',
            'quantity': 'quantity',
            'quantite_min': 'min_quantity',
            'min_quantity': 'min_quantity',
            'unite': 'unit',
            'unit': 'unit',
            'prix_achat': 'purchase_price',
            'purchase_price': 'purchase_price',
            'prix_vente': 'selling_price',
            'selling_price': 'selling_price',
            'date_fabrication': 'manufacturing_date',
            'manufacturing_date': 'manufacturing_date',
            'date_expiration': 'expiry_date',
            'expiry_date': 'expiry_date',
            'ordonnance_requise': 'is_prescription_required',
            'is_prescription_required': 'is_prescription_required',
        }
        
        # Renommer les colonnes
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # Vérifier les colonnes requises
        if 'name' not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Colonne 'nom' ou 'name' requise"
            )
        if 'purchase_price' not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Colonne 'prix_achat' ou 'purchase_price' requise"
            )
        if 'selling_price' not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Colonne 'prix_vente' ou 'selling_price' requise"
            )
        
        # Traiter chaque ligne
        created_count = 0
        error_count = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Valeurs par défaut
                name = str(row['name']).strip()
                if not name or name == 'nan':
                    continue
                
                # Convertir les valeurs
                purchase_price = float(row['purchase_price']) if pd.notna(row['purchase_price']) else 0
                selling_price = float(row['selling_price']) if pd.notna(row['selling_price']) else 0
                quantity = int(row.get('quantity', 0)) if pd.notna(row.get('quantity', 0)) else 0
                min_quantity = int(row.get('min_quantity', 0)) if pd.notna(row.get('min_quantity', 0)) else 0
                
                # Unité
                unit_str = str(row.get('unit', 'unit')).lower().strip() if pd.notna(row.get('unit')) else 'unit'
                try:
                    unit = ProductUnit(unit_str)
                except ValueError:
                    unit = ProductUnit.UNIT
                
                # Dates
                manufacturing_date = None
                if 'manufacturing_date' in row and pd.notna(row['manufacturing_date']):
                    try:
                        manufacturing_date = pd.to_datetime(row['manufacturing_date']).to_pydatetime()
                    except:
                        pass
                
                expiry_date = None
                if 'expiry_date' in row and pd.notna(row['expiry_date']):
                    try:
                        expiry_date = pd.to_datetime(row['expiry_date']).to_pydatetime()
                    except:
                        pass
                
                # Booléen
                is_prescription_required = False
                if 'is_prescription_required' in row and pd.notna(row['is_prescription_required']):
                    val = str(row['is_prescription_required']).lower().strip()
                    is_prescription_required = val in ['true', '1', 'oui', 'yes', 'o']
                
                # Créer le produit
                product = Product(
                    pharmacy_id=pharmacy_id,
                    name=name,
                    description=str(row.get('description', '')).strip() if pd.notna(row.get('description')) else None,
                    barcode=str(row.get('barcode', '')).strip() if pd.notna(row.get('barcode')) and str(row.get('barcode', '')).strip() != 'nan' else None,
                    sku=str(row.get('sku', '')).strip() if pd.notna(row.get('sku')) and str(row.get('sku', '')).strip() != 'nan' else None,
                    quantity=quantity,
                    min_quantity=min_quantity,
                    unit=unit,
                    purchase_price=purchase_price,
                    selling_price=selling_price,
                    manufacturing_date=manufacturing_date,
                    expiry_date=expiry_date,
                    is_prescription_required=is_prescription_required,
                    is_active=True,
                )
                
                db.add(product)
                created_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"Ligne {idx + 2}: {str(e)}")
                continue
        
        db.commit()
        
        return {
            "success": True,
            "created": created_count,
            "errors": error_count,
            "error_details": errors[:10],  # Limiter à 10 erreurs
            "message": f"{created_count} produit(s) importé(s) avec succès"
        }
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de l'import: {str(e)}"
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
    from app.models.sale import Sale
    from app.models.cash_register import CashSession
    from app.models.stock import StockAdjustment
    
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pharmacie non trouvée"
        )
    
    try:
        # 1. Supprimer les ventes de la pharmacie (qui référencent les utilisateurs)
        db.query(Sale).filter(Sale.pharmacy_id == pharmacy_id).delete(synchronize_session=False)
        
        # 2. Supprimer les sessions de caisse (qui référencent les utilisateurs)
        db.query(CashSession).filter(CashSession.pharmacy_id == pharmacy_id).delete(synchronize_session=False)
        
        # 3. Supprimer les ajustements de stock (qui référencent les utilisateurs)
        db.query(StockAdjustment).filter(StockAdjustment.pharmacy_id == pharmacy_id).delete(synchronize_session=False)
        
        # 4. Supprimer les utilisateurs associés
        db.query(User).filter(User.pharmacy_id == pharmacy_id).delete(synchronize_session=False)
        
        # 5. Supprimer la pharmacie (cascade supprimera produits, clients, etc.)
        db.delete(pharmacy)
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Impossible de supprimer le commerce: {str(e)}"
        )
    
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


# ============ LICENCES ============

import secrets
import string

def generate_license_key():
    """Génère une clé de licence unique de 16 caractères."""
    chars = string.ascii_uppercase + string.digits
    return '-'.join(''.join(secrets.choice(chars) for _ in range(4)) for _ in range(4))


class LicenseCreateRequest(BaseModel):
    """Données pour créer une licence."""
    pharmacy_id: Optional[int] = None
    max_activations: int = 2
    expires_at: Optional[datetime] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    notes: Optional[str] = None


class LicenseWithPharmacy(BaseModel):
    """Licence avec nom du commerce."""
    id: int
    license_key: str
    pharmacy_id: Optional[int]
    pharmacy_name: Optional[str] = None
    status: str
    max_activations: int
    activations_count: int = 0
    expires_at: Optional[datetime]
    customer_name: Optional[str]
    customer_email: Optional[str]
    customer_phone: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/licenses", response_model=LicenseWithPharmacy, summary="Générer une licence")
def create_license(
    data: LicenseCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Génère une nouvelle licence.
    """
    # Générer une clé unique
    license_key = generate_license_key()
    
    # Vérifier que la clé n'existe pas déjà
    while db.query(License).filter(License.license_key == license_key).first():
        license_key = generate_license_key()
    
    # Créer la licence
    license = License(
        license_key=license_key,
        pharmacy_id=data.pharmacy_id,
        status="active",
        max_activations=data.max_activations,
        expires_at=data.expires_at,
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        customer_phone=data.customer_phone,
        notes=data.notes,
    )
    
    db.add(license)
    db.commit()
    db.refresh(license)
    
    # Récupérer le nom du commerce si associé
    pharmacy_name = None
    if license.pharmacy_id:
        pharmacy = db.query(Pharmacy).filter(Pharmacy.id == license.pharmacy_id).first()
        if pharmacy:
            pharmacy_name = pharmacy.name
    
    return LicenseWithPharmacy(
        id=license.id,
        license_key=license.license_key,
        pharmacy_id=license.pharmacy_id,
        pharmacy_name=pharmacy_name,
        status=license.status,
        max_activations=license.max_activations,
        activations_count=0,
        expires_at=license.expires_at,
        customer_name=license.customer_name,
        customer_email=license.customer_email,
        customer_phone=license.customer_phone,
        notes=license.notes,
        created_at=license.created_at,
        updated_at=license.updated_at,
    )


@router.get("/licenses", response_model=List[LicenseWithPharmacy], summary="Liste des licences")
def list_licenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
) -> Any:
    """
    Liste toutes les licences.
    """
    from app.models.license import LicenseActivation
    
    query = db.query(License)
    
    if search:
        query = query.filter(
            License.license_key.ilike(f"%{search}%") |
            License.customer_name.ilike(f"%{search}%") |
            License.customer_email.ilike(f"%{search}%")
        )
    
    licenses = query.order_by(License.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for lic in licenses:
        # Récupérer le nom du commerce
        pharmacy_name = None
        if lic.pharmacy_id:
            pharmacy = db.query(Pharmacy).filter(Pharmacy.id == lic.pharmacy_id).first()
            if pharmacy:
                pharmacy_name = pharmacy.name
        
        # Compter les activations
        activations_count = db.query(LicenseActivation).filter(
            LicenseActivation.license_id == lic.id,
            LicenseActivation.is_active == True
        ).count()
        
        result.append(LicenseWithPharmacy(
            id=lic.id,
            license_key=lic.license_key,
            pharmacy_id=lic.pharmacy_id,
            pharmacy_name=pharmacy_name,
            status=lic.status,
            max_activations=lic.max_activations,
            activations_count=activations_count,
            expires_at=lic.expires_at,
            customer_name=lic.customer_name,
            customer_email=lic.customer_email,
            customer_phone=lic.customer_phone,
            notes=lic.notes,
            created_at=lic.created_at,
            updated_at=lic.updated_at,
        ))
    
    return result


@router.get("/licenses/{license_id}", summary="Détails d'une licence")
def get_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Récupère les détails d'une licence avec ses activations.
    """
    from app.models.license import LicenseActivation
    
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Licence non trouvée"
        )
    
    # Récupérer le nom du commerce
    pharmacy_name = None
    if license.pharmacy_id:
        pharmacy = db.query(Pharmacy).filter(Pharmacy.id == license.pharmacy_id).first()
        if pharmacy:
            pharmacy_name = pharmacy.name
    
    # Récupérer les activations
    activations = db.query(LicenseActivation).filter(
        LicenseActivation.license_id == license.id
    ).all()
    
    return {
        "id": license.id,
        "license_key": license.license_key,
        "pharmacy_id": license.pharmacy_id,
        "pharmacy_name": pharmacy_name,
        "status": license.status,
        "max_activations": license.max_activations,
        "expires_at": license.expires_at,
        "customer_name": license.customer_name,
        "customer_email": license.customer_email,
        "customer_phone": license.customer_phone,
        "notes": license.notes,
        "created_at": license.created_at,
        "updated_at": license.updated_at,
        "activations": [
            {
                "id": act.id,
                "hardware_id": act.hardware_id,
                "machine_name": act.machine_name,
                "os_info": act.os_info,
                "is_active": act.is_active,
                "activated_at": act.activated_at,
                "last_verified_at": act.last_verified_at,
                "deactivated_at": act.deactivated_at,
            }
            for act in activations
        ]
    }


@router.put("/licenses/{license_id}", response_model=LicenseWithPharmacy, summary="Modifier une licence")
def update_license(
    license_id: int,
    data: LicenseCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Modifie une licence existante.
    """
    from app.models.license import LicenseActivation
    
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Licence non trouvée"
        )
    
    # Mettre à jour les champs
    if data.pharmacy_id is not None:
        license.pharmacy_id = data.pharmacy_id
    license.max_activations = data.max_activations
    license.expires_at = data.expires_at
    license.customer_name = data.customer_name
    license.customer_email = data.customer_email
    license.customer_phone = data.customer_phone
    license.notes = data.notes
    
    db.commit()
    db.refresh(license)
    
    # Récupérer le nom du commerce
    pharmacy_name = None
    if license.pharmacy_id:
        pharmacy = db.query(Pharmacy).filter(Pharmacy.id == license.pharmacy_id).first()
        if pharmacy:
            pharmacy_name = pharmacy.name
    
    # Compter les activations
    activations_count = db.query(LicenseActivation).filter(
        LicenseActivation.license_id == license.id,
        LicenseActivation.is_active == True
    ).count()
    
    return LicenseWithPharmacy(
        id=license.id,
        license_key=license.license_key,
        pharmacy_id=license.pharmacy_id,
        pharmacy_name=pharmacy_name,
        status=license.status,
        max_activations=license.max_activations,
        activations_count=activations_count,
        expires_at=license.expires_at,
        customer_name=license.customer_name,
        customer_email=license.customer_email,
        customer_phone=license.customer_phone,
        notes=license.notes,
        created_at=license.created_at,
        updated_at=license.updated_at,
    )


@router.delete("/licenses/{license_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer une licence")
def delete_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Response:
    """
    Supprime une licence et toutes ses activations.
    """
    from app.models.license import LicenseActivation
    
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Licence non trouvée"
        )
    
    # Supprimer les activations
    db.query(LicenseActivation).filter(LicenseActivation.license_id == license_id).delete()
    
    # Supprimer la licence
    db.delete(license)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/licenses/{license_id}/revoke", summary="Révoquer une licence")
def revoke_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Révoque une licence (la désactive).
    """
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Licence non trouvée"
        )
    
    license.status = "revoked"
    db.commit()
    
    return {"message": "Licence révoquée avec succès"}


@router.post("/licenses/{license_id}/reactivate", summary="Réactiver une licence")
def reactivate_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Réactive une licence révoquée.
    """
    license = db.query(License).filter(License.id == license_id).first()
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Licence non trouvée"
        )
    
    license.status = "active"
    db.commit()
    
    return {"message": "Licence réactivée avec succès"}

