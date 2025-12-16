#!/usr/bin/env python3
"""Script pour créer l'admin dans la base SQLite"""
import os
import sys
from pathlib import Path

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

# Définir l'environnement
os.environ.setdefault('DATABASE_URL', 'sqlite:///./data/pharmacie.db')
os.environ.setdefault('SECRET_KEY', 'local-electron-secret-key')
os.environ.setdefault('ENVIRONMENT', 'production')
os.environ.setdefault('DEBUG', 'false')

from app.db.base import Base, engine, SessionLocal
from app.models.user import User
from app.models.pharmacy import Pharmacy
from app.core.security import get_password_hash

def create_admin():
    """Crée l'admin et la pharmacie si nécessaire"""
    
    # Créer le dossier data s'il n'existe pas
    data_dir = Path(__file__).parent / 'data'
    data_dir.mkdir(exist_ok=True)
    
    # Créer toutes les tables
    print("📦 Création des tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées")
    
    db = SessionLocal()
    try:
        # Vérifier si une pharmacie existe
        pharmacy = db.query(Pharmacy).first()
        if not pharmacy:
            print("🏥 Création de la pharmacie par défaut...")
            pharmacy = Pharmacy(
                name="Ma Pharmacie",
                address="Adresse à configurer",
                phone="00 00 00 00 00",
                email="contact@mapharmacie.com",
                license_number="PHARMA-001",
                is_active=True
            )
            db.add(pharmacy)
            db.commit()
            db.refresh(pharmacy)
            print(f"  ✅ Pharmacie créée: {pharmacy.name} (ID: {pharmacy.id})")
        else:
            print(f"  ℹ️  Pharmacie existante: {pharmacy.name} (ID: {pharmacy.id})")
        
        # Vérifier si un admin existe
        admin = db.query(User).filter(User.email == "admin@pharmacie-manager.com").first()
        if not admin:
            print("👤 Création de l'admin...")
            admin = User(
                email="admin@pharmacie-manager.com",
                username="admin",
                full_name="Administrateur",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                pharmacy_id=pharmacy.id,
                is_active=True,
                is_superuser=True
            )
            db.add(admin)
            db.commit()
            print("  ✅ Admin créé!")
        else:
            print(f"  ℹ️  Admin existant: {admin.email}")
            # Corriger l'email si nécessaire
            if admin.email != "admin@pharmacie-manager.com":
                admin.email = "admin@pharmacie-manager.com"
                db.commit()
                print("  ✅ Email corrigé")
        
        print("\n" + "=" * 50)
        print("✅ Configuration terminée!")
        print("=" * 50)
        print("\n📋 Identifiants de connexion:")
        print("   Email: admin@pharmacie-manager.com")
        print("   Mot de passe: admin123")
        print("\n⚠️  IMPORTANT: Changez ce mot de passe après la première connexion!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()

