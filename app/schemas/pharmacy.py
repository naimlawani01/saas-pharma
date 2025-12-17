from typing import Optional
from datetime import datetime
from pydantic import BaseModel


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


class PharmacyBase(BaseModel):
    """
    Schéma de base pour les commerces.
    Note: Le nom 'Pharmacy' est conservé pour compatibilité,
    mais représente tout type de commerce.
    """
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "Guinée"
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    business_type: str = "general"  # Type d'activité


class PharmacyCreate(PharmacyBase):
    pass


class PharmacyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    license_number: Optional[str] = None
    business_type: Optional[str] = None
    is_active: Optional[bool] = None


class Pharmacy(PharmacyBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime] = None

    class Config:
        from_attributes = True
