"""
Script pour créer un super administrateur dans la base de données.
À utiliser sur Railway ou en production pour créer le premier super admin.
"""
import sys
import os
from pathlib import Path

# Ajouter le répertoire backend au path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash


def create_superadmin():
    """Créer un super administrateur."""
    db: Session = SessionLocal()
    
    try:
        # Vérifier si un super admin existe déjà
        existing_superadmin = db.query(User).filter(User.is_superuser == True).first()
        if existing_superadmin:
            print(f"⚠️  Un super administrateur existe déjà: {existing_superadmin.username} ({existing_superadmin.email})")
            print("   Pour créer un nouveau super admin, supprimez d'abord l'existant ou modifiez ce script.")
            return
        
        # Récupérer les informations depuis les variables d'environnement ou utiliser des valeurs par défaut
        username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
        email = os.getenv("SUPERADMIN_EMAIL", "admin@pharmaciemanager.com")
        password = os.getenv("SUPERADMIN_PASSWORD", "superadmin123")
        full_name = os.getenv("SUPERADMIN_FULL_NAME", "Super Administrateur")
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"⚠️  Un utilisateur avec ce nom d'utilisateur ou cet email existe déjà: {existing_user.username}")
            # Mettre à jour pour en faire un super admin
            existing_user.is_superuser = True
            existing_user.pharmacy_id = None  # Super admin n'a pas de pharmacie
            existing_user.hashed_password = get_password_hash(password)
            db.commit()
            print(f"✅ Utilisateur mis à jour en super administrateur: {username}")
            print(f"   Email: {email}")
            print(f"   Mot de passe: {password}")
            return
        
        # Créer le super admin
        superadmin = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=True,
            pharmacy_id=None,  # Super admin n'est pas associé à une pharmacie
        )
        
        db.add(superadmin)
        db.commit()
        db.refresh(superadmin)
        
        print("\n✅ Super administrateur créé avec succès!\n")
        print("📋 Informations de connexion:")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Mot de passe: {password}")
        print(f"   Nom complet: {full_name}")
        print("\n⚠️  IMPORTANT: Changez le mot de passe après la première connexion!")
        print("\n💡 Pour personnaliser les identifiants, définissez ces variables d'environnement:")
        print("   - SUPERADMIN_USERNAME")
        print("   - SUPERADMIN_EMAIL")
        print("   - SUPERADMIN_PASSWORD")
        print("   - SUPERADMIN_FULL_NAME")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Erreur lors de la création du super admin: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_superadmin()

