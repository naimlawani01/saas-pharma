"""
Module de sécurité pour Pharmacie Manager.
Gestion de l'authentification JWT et du hashage des mots de passe.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from jose import JWTError, jwt
import bcrypt
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si un mot de passe en clair correspond au hash stocké.
    
    Args:
        plain_password: Mot de passe en clair
        hashed_password: Hash du mot de passe stocké
        
    Returns:
        True si le mot de passe est correct, False sinon
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash un mot de passe pour le stockage sécurisé.
    
    Args:
        password: Mot de passe en clair
        
    Returns:
        Hash du mot de passe
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(
    subject: Union[str, int],
    role: str,
    pharmacy_id: Optional[int] = None,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Crée un token JWT d'accès.
    
    Args:
        subject: Identifiant de l'utilisateur (généralement l'ID)
        role: Rôle de l'utilisateur
        pharmacy_id: ID de la pharmacie de l'utilisateur
        expires_delta: Durée de validité du token
        extra_claims: Claims supplémentaires à inclure
        
    Returns:
        Token JWT encodé
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "sub": str(subject),
        "role": role,
        "pharmacy_id": pharmacy_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    
    if extra_claims:
        to_encode.update(extra_claims)
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Crée un token JWT de rafraîchissement.
    
    Args:
        subject: Identifiant de l'utilisateur
        expires_delta: Durée de validité du token
        
    Returns:
        Token JWT de rafraîchissement encodé
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)  # 7 jours par défaut
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Vérifie et décode un token JWT.
    
    Args:
        token: Token JWT à vérifier
        token_type: Type de token attendu (access ou refresh)
        
    Returns:
        Payload du token si valide, None sinon
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Vérifier le type de token
        if payload.get("type") != token_type:
            return None
        
        return payload
        
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[dict]:
    """
    Décode un token d'accès JWT (compatibilité).
    """
    return verify_token(token, token_type="access")
