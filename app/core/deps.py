"""
Dépendances FastAPI pour l'injection de dépendances.
Gère l'authentification, les autorisations et l'accès à la base de données.
Style Kobiri adapté pour Pharmacie Manager.
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import verify_token
from app.db.base import get_db
from app.models.user import User

# Schéma de sécurité Bearer Token
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Récupère l'utilisateur courant à partir du token JWT.
    
    Args:
        credentials: Token Bearer JWT
        db: Session de base de données
        
    Returns:
        Instance User de l'utilisateur authentifié
        
    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur non trouvé
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token d'authentification invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token = credentials.credentials
    payload = verify_token(token, token_type="access")
    
    if payload is None:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if user is None:
        raise credentials_exception
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Vérifie que l'utilisateur actuel est actif."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def get_current_pharmacy_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Vérifie que l'utilisateur appartient à une pharmacie."""
    if current_user.pharmacy_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must be associated with a pharmacy"
        )
    return current_user


def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Vérifie que l'utilisateur est un superutilisateur."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
