"""
Routes d'authentification - Inscription, connexion, tokens.
Style Kobiri adapté pour Pharmacie Manager.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    verify_token,
)
from app.core.deps import get_current_active_user, get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.token import Token, RefreshTokenRequest
from app.schemas.user import (
    User as UserSchema,
    UserCreate,
    UserLogin,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Inscription d'un nouvel utilisateur",
)
def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate
) -> Any:
    """
    Crée un nouveau compte utilisateur.
    
    - **email**: Adresse email unique
    - **username**: Nom d'utilisateur unique
    - **password**: Mot de passe (min 6 caractères)
    - **full_name**: Nom complet (optionnel)
    - **pharmacy_id**: ID de la pharmacie (optionnel)
    """
    # Vérifier si l'email existe déjà
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte existe déjà avec cet email",
        )
    
    # Vérifier si le username existe déjà
    existing_username = db.query(User).filter(User.username == user_in.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce nom d'utilisateur est déjà pris",
        )
    
    # Créer l'utilisateur
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        pharmacy_id=user_in.pharmacy_id,
        is_active=True,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Connexion utilisateur",
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> Any:
    """
    Authentifie un utilisateur et retourne les tokens JWT.
    
    Peut se connecter avec email OU username.
    """
    # Trouver l'utilisateur par email ou username
    user = None
    if credentials.email:
        user = db.query(User).filter(User.email == credentials.email).first()
    elif credentials.username:
        user = db.query(User).filter(User.username == credentials.username).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ou nom d'utilisateur requis",
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email/utilisateur ou mot de passe incorrect",
        )
    
    # Vérifier le mot de passe
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email/utilisateur ou mot de passe incorrect",
        )
    
    # Vérifier si le compte est actif
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte a été désactivé",
        )
    
    # Mettre à jour la date de dernière connexion
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Générer les tokens
    access_token = create_access_token(
        subject=user.id,
        role=user.role.value,
        pharmacy_id=user.pharmacy_id,
    )
    refresh_token = create_refresh_token(subject=user.id)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login/form",
    response_model=Token,
    summary="Connexion avec formulaire OAuth2",
)
def login_form(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Authentification via formulaire OAuth2 (pour Swagger UI).
    Le username peut être un email ou un nom d'utilisateur.
    """
    # Trouver l'utilisateur par email ou username
    user = db.query(User).filter(
        (User.email == form_data.username) | (User.username == form_data.username)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email/utilisateur ou mot de passe incorrect",
        )
    
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email/utilisateur ou mot de passe incorrect",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte a été désactivé",
        )
    
    # Mettre à jour la date de dernière connexion
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Générer les tokens
    access_token = create_access_token(
        subject=user.id,
        role=user.role.value,
        pharmacy_id=user.pharmacy_id,
    )
    refresh_token = create_refresh_token(subject=user.id)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Rafraîchir le token d'accès",
)
def refresh_token(
    token_request: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    Génère un nouveau token d'accès à partir du refresh token.
    """
    payload = verify_token(token_request.refresh_token, token_type="refresh")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré",
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé ou désactivé",
        )
    
    # Générer de nouveaux tokens
    access_token = create_access_token(
        subject=user.id,
        role=user.role.value,
        pharmacy_id=user.pharmacy_id,
    )
    new_refresh_token = create_refresh_token(subject=user.id)
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserSchema,
    summary="Profil de l'utilisateur connecté",
)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retourne les informations de l'utilisateur connecté.
    """
    return current_user


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Changer le mot de passe",
)
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Change le mot de passe de l'utilisateur connecté.
    """
    # Vérifier l'ancien mot de passe
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )
    
    # Mettre à jour le mot de passe
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Mot de passe mis à jour avec succès"}


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Demander la réinitialisation du mot de passe",
)
def forgot_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db),
) -> Any:
    """
    Génère un code de réinitialisation du mot de passe.
    Dans une vraie app, envoyez ce code par email/SMS.
    """
    import random
    
    user = None
    if reset_data.email:
        user = db.query(User).filter(User.email == reset_data.email).first()
    
    # Pour des raisons de sécurité, ne pas révéler si l'utilisateur existe
    if user:
        # Générer un code à 6 chiffres
        reset_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        user.reset_token = reset_code
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        # TODO: Envoyer le code par email/SMS
        # En développement, on peut le retourner (à retirer en production)
        return {
            "message": "Si un compte existe avec cet email, vous recevrez un code de réinitialisation",
            "debug_code": reset_code  # À RETIRER EN PRODUCTION
        }
    
    return {
        "message": "Si un compte existe avec cet email, vous recevrez un code de réinitialisation"
    }


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Réinitialiser le mot de passe avec le code",
)
def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db),
) -> Any:
    """
    Réinitialise le mot de passe avec le code reçu.
    """
    # Trouver l'utilisateur par email
    user = db.query(User).filter(User.email == reset_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email non trouvé",
        )
    
    # Vérifier le code
    if not user.reset_token or user.reset_token != reset_data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code de réinitialisation invalide",
        )
    
    # Vérifier l'expiration
    if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le code a expiré. Veuillez en demander un nouveau.",
        )
    
    # Mettre à jour le mot de passe
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {"message": "Mot de passe réinitialisé avec succès"}


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Déconnexion",
)
def logout(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Déconnecte l'utilisateur.
    Note: Avec JWT, la déconnexion est gérée côté client en supprimant le token.
    """
    return {"message": "Déconnexion réussie"}
