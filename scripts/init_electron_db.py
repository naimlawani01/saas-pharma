"""
Script d'initialisation de la base de données SQLite pour le mode Electron.

Ce script:
1. Crée le dossier data/ s'il n'existe pas
2. Initialise la base de données SQLite
3. Crée les tables via SQLAlchemy
4. Crée un super admin par défaut

Usage:
    python scripts/init_electron_db.py
"""

import os
import sys
from pathlib import Path

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Définir l'environnement avant les imports
os.environ.setdefault('DATABASE_URL', 'sqlite:///./data/pharmacie.db')
os.environ.setdefault('SECRET_KEY', 'local-electron-secret-key')
os.environ.setdefault('ENVIRONMENT', 'production')
os.environ.setdefault('DEBUG', 'false')

from app.db.base import Base, engine, SessionLocal
from app.models.user import User
from app.models.pharmacy import Pharmacy
from app.core.security import get_password_hash


def init_database():
    """Initialise la base de données SQLite."""
    
    # Créer le dossier data s'il n'existe pas
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(exist_ok=True)
    print(f"✅ Dossier data créé: {data_dir}")
    
    # Créer toutes les tables
    print("📦 Création des tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées avec succès")
    
    # Créer un super admin par défaut s'il n'existe pas
    db = SessionLocal()
    try:
        # Vérifier si un super admin existe
        existing_admin = db.query(User).filter(User.is_superuser == True).first()
        
        if not existing_admin:
            print("👤 Création du super admin par défaut...")
            
            # Créer une pharmacie par défaut d'abord
            default_pharmacy = db.query(Pharmacy).filter(Pharmacy.name == "Ma Pharmacie").first()
            if not default_pharmacy:
                default_pharmacy = Pharmacy(
                    name="Ma Pharmacie",
                    address="Adresse à configurer",
                    phone="00 00 00 00 00",
                    email="contact@mapharmacie.com",
                    license_number="PHARMA-001",
                    is_active=True
                )
                db.add(default_pharmacy)
                db.commit()
                db.refresh(default_pharmacy)
                print(f"  ✅ Pharmacie créée: {default_pharmacy.name}")
            
            # Créer le super admin
            admin = User(
                email="admin@pharmacie-manager.com",
                username="admin",
                full_name="Administrateur",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                pharmacy_id=default_pharmacy.id,
                is_active=True,
                is_superuser=True
            )
            db.add(admin)
            db.commit()
            
            print("  ✅ Super admin créé:")
            print("     Email: admin@pharmacie-manager.com")
            print("     Mot de passe: admin123")
            print("     ⚠️  IMPORTANT: Changez ce mot de passe après la première connexion!")
        else:
            print(f"ℹ️  Super admin existant: {existing_admin.email}")
            
    finally:
        db.close()
    
    print("\n" + "=" * 50)
    print("🎉 Base de données initialisée avec succès!")
    print("=" * 50)


if __name__ == "__main__":
    init_database()

