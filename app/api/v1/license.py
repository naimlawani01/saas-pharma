"""
Endpoints pour la gestion des licences - Activation et vérification.
"""
from typing import Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import secrets
import hashlib

from app.core.deps import get_db, get_current_pharmacy_user
from app.models.user import User
from app.models.license import License, LicenseActivation
from app.schemas.license import (
    LicenseActivateRequest,
    LicenseActivateResponse,
    LicenseVerifyRequest,
    LicenseVerifyResponse,
)

router = APIRouter()


def generate_activation_token() -> str:
    """Génère un token d'activation unique et sécurisé."""
    return secrets.token_urlsafe(32)


def hash_hardware_id(hardware_id: str) -> str:
    """Hash le hardware_id pour le stockage (optionnel, pour plus de sécurité)."""
    return hashlib.sha256(hardware_id.encode()).hexdigest()


@router.post(
    "/activate",
    response_model=LicenseActivateResponse,
    status_code=status.HTTP_200_OK,
    summary="Activer une licence sur une machine",
)
def activate_license(
    *,
    db: Session = Depends(get_db),
    request: LicenseActivateRequest,
) -> Any:
    """
    Active une licence sur une machine spécifique.
    
    - Vérifie que la clé de licence existe et est valide
    - Vérifie que la licence n'a pas expiré
    - Vérifie que le nombre maximum d'activations n'est pas atteint
    - Crée une nouvelle activation ou réactive une activation existante
    """
    # Rechercher la licence
    license = db.query(License).filter(
        License.license_key == request.license_key.upper().strip()
    ).first()
    
    if not license:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clé de licence invalide ou introuvable."
        )
    
    # Vérifier le statut de la licence
    if license.status not in ["active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cette licence est {license.status}. Contactez le support."
        )
    
    # Vérifier l'expiration
    if license.expires_at and license.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette licence a expiré. Veuillez la renouveler."
        )
    
    # Vérifier si cette machine est déjà activée
    existing_activation = db.query(LicenseActivation).filter(
        LicenseActivation.license_id == license.id,
        LicenseActivation.hardware_id == request.hardware_id,
        LicenseActivation.is_active == True
    ).first()
    
    if existing_activation:
        # Réactiver si elle était désactivée, ou retourner le token existant
        if not existing_activation.is_active:
            existing_activation.is_active = True
            existing_activation.activated_at = datetime.now(timezone.utc)
            existing_activation.deactivated_at = None
            db.commit()
            db.refresh(existing_activation)
        
        return LicenseActivateResponse(
            success=True,
            message="Licence déjà activée sur cette machine.",
            activation_token=existing_activation.activation_token,
            license_id=license.id
        )
    
    # Compter les activations actives
    active_count = db.query(LicenseActivation).filter(
        LicenseActivation.license_id == license.id,
        LicenseActivation.is_active == True
    ).count()
    
    # Vérifier la limite d'activations
    if active_count >= license.max_activations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Nombre maximum d'activations atteint ({license.max_activations}). "
                   f"Veuillez désactiver une machine existante ou contacter le support."
        )
    
    # Créer une nouvelle activation
    activation_token = generate_activation_token()
    new_activation = LicenseActivation(
        license_id=license.id,
        hardware_id=request.hardware_id,
        machine_name=request.machine_name,
        os_info=request.os_info,
        is_active=True,
        activation_token=activation_token,
        activated_at=datetime.now(timezone.utc),
        last_verified_at=datetime.now(timezone.utc)
    )
    
    db.add(new_activation)
    db.commit()
    db.refresh(new_activation)
    
    return LicenseActivateResponse(
        success=True,
        message="Licence activée avec succès.",
        activation_token=activation_token,
        license_id=license.id
    )


@router.post(
    "/verify",
    response_model=LicenseVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Vérifier la validité d'une licence",
)
def verify_license(
    *,
    db: Session = Depends(get_db),
    request: LicenseVerifyRequest,
) -> Any:
    """
    Vérifie la validité d'une licence pour une machine donnée.
    
    Utilisé lors de la synchronisation ou au démarrage de l'application.
    """
    # Rechercher l'activation par hardware_id ou activation_token
    activation = None
    
    if request.activation_token:
        activation = db.query(LicenseActivation).filter(
            LicenseActivation.activation_token == request.activation_token,
            LicenseActivation.is_active == True
        ).first()
    else:
        activation = db.query(LicenseActivation).filter(
            LicenseActivation.hardware_id == request.hardware_id,
            LicenseActivation.is_active == True
        ).first()
    
    if not activation:
        return LicenseVerifyResponse(
            valid=False,
            message="Aucune activation trouvée pour cette machine. Veuillez activer votre licence."
        )
    
    # Charger la licence
    license = db.query(License).filter(License.id == activation.license_id).first()
    
    if not license:
        return LicenseVerifyResponse(
            valid=False,
            message="Licence introuvable."
        )
    
    # Vérifier le statut de la licence
    if license.status not in ["active"]:
        return LicenseVerifyResponse(
            valid=False,
            message=f"Cette licence est {license.status}. Contactez le support.",
            license_status=license.status
        )
    
    # Vérifier l'expiration
    if license.expires_at and license.expires_at < datetime.now(timezone.utc):
        return LicenseVerifyResponse(
            valid=False,
            message="Cette licence a expiré. Veuillez la renouveler.",
            license_status="expired",
            expires_at=license.expires_at
        )
    
    # Mettre à jour la date de dernière vérification
    activation.last_verified_at = datetime.now(timezone.utc)
    db.commit()
    
    # Compter les activations actives
    active_count = db.query(LicenseActivation).filter(
        LicenseActivation.license_id == license.id,
        LicenseActivation.is_active == True
    ).count()
    
    return LicenseVerifyResponse(
        valid=True,
        message="Licence valide.",
        license_status=license.status,
        expires_at=license.expires_at,
        activations_count=active_count,
        max_activations=license.max_activations
    )


@router.post(
    "/deactivate",
    status_code=status.HTTP_200_OK,
    summary="Désactiver une licence sur une machine",
)
def deactivate_license(
    *,
    db: Session = Depends(get_db),
    request: LicenseVerifyRequest,
) -> Any:
    """
    Désactive une licence sur une machine spécifique.
    
    Permet de libérer une activation pour l'utiliser sur une autre machine.
    """
    # Rechercher l'activation
    activation = None
    
    if request.activation_token:
        activation = db.query(LicenseActivation).filter(
            LicenseActivation.activation_token == request.activation_token,
            LicenseActivation.is_active == True
        ).first()
    else:
        activation = db.query(LicenseActivation).filter(
            LicenseActivation.hardware_id == request.hardware_id,
            LicenseActivation.is_active == True
        ).first()
    
    if not activation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune activation active trouvée pour cette machine."
        )
    
    # Désactiver
    activation.is_active = False
    activation.deactivated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {
        "success": True,
        "message": "Licence désactivée avec succès sur cette machine."
    }

