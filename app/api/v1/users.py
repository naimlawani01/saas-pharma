"""
Endpoints pour la gestion des utilisateurs (Admin uniquement)
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.core.deps import get_current_active_user, get_db
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.schemas.user import User as UserSchema, UserUpdate

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Vérifie que l'utilisateur est admin"""
    if current_user.role != UserRole.ADMIN and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous devez être administrateur pour effectuer cette action"
        )
    return current_user


@router.get("/", response_model=List[UserSchema], summary="Lister les utilisateurs")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Liste tous les utilisateurs de la pharmacie.
    Réservé aux administrateurs.
    """
    # Filtrer par pharmacie si l'utilisateur n'est pas superuser
    query = db.query(User)
    if not current_user.is_superuser and current_user.pharmacy_id:
        query = query.filter(User.pharmacy_id == current_user.pharmacy_id)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserSchema, summary="Détail d'un utilisateur")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Any:
    """
    Récupère les détails d'un utilisateur.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Vérifier que l'utilisateur est de la même pharmacie
    if not current_user.is_superuser and user.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez pas accéder à cet utilisateur"
        )
    
    return user


@router.put("/{user_id}", response_model=UserSchema, summary="Modifier un utilisateur")
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Any:
    """
    Met à jour les informations d'un utilisateur.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Vérifier que l'utilisateur est de la même pharmacie
    if not current_user.is_superuser and user.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez pas modifier cet utilisateur"
        )
    
    # Empêcher de modifier son propre statut actif
    if user.id == current_user.id and user_update.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas désactiver votre propre compte"
        )
    
    # Vérifier l'unicité de l'email si modifié
    if user_update.email and user_update.email != user.email:
        if db.query(User).filter(User.email == user_update.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cet email est déjà utilisé"
            )
    
    # Vérifier l'unicité du username si modifié
    if user_update.username and user_update.username != user.username:
        if db.query(User).filter(User.username == user_update.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce nom d'utilisateur est déjà utilisé"
            )
    
    # Mettre à jour les champs
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un utilisateur")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Response:
    """
    Supprime un utilisateur.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Empêcher de se supprimer soi-même
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas supprimer votre propre compte"
        )
    
    # Vérifier que l'utilisateur est de la même pharmacie
    if not current_user.is_superuser and user.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez pas supprimer cet utilisateur"
        )
    
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{user_id}/reset-password", summary="Réinitialiser le mot de passe")
def reset_user_password(
    user_id: int,
    password_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Any:
    """
    Réinitialise le mot de passe d'un utilisateur (admin uniquement).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    
    # Vérifier que l'utilisateur est de la même pharmacie
    if not current_user.is_superuser and user.pharmacy_id != current_user.pharmacy_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez pas modifier cet utilisateur"
        )
    
    new_password = password_data.get("new_password")
    if not new_password or len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins 6 caractères"
        )
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {"message": "Mot de passe réinitialisé avec succès"}

