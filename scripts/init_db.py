"""
Script pour initialiser la base de données avec un superutilisateur.
"""
import sys
from pathlib import Path

# Ajouter le répertoire backend au path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.db.base import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.pharmacy import Pharmacy
from app.core.security import get_password_hash


def init_db() -> None:
    """Initialise la base de données avec les tables et un superutilisateur."""
    # Créer les tables
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Vérifier si un superutilisateur existe déjà
        superuser = db.query(User).filter(User.is_superuser == True).first()
        if superuser:
            print("Superutilisateur déjà existant.")
            return
        
        # Créer une pharmacie par défaut
        default_pharmacy = Pharmacy(
            name="Pharmacie Principale",
            address="Adresse par défaut",
            city="Conakry",
            country="Guinée",
            is_active=True
        )
        db.add(default_pharmacy)
        db.flush()
        
        # Créer le superutilisateur
        superuser = User(
            email="admin@pharmacie-manager.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            full_name="Administrateur",
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=True,
            pharmacy_id=default_pharmacy.id
        )
        db.add(superuser)
        db.commit()
        
        print("✅ Base de données initialisée avec succès!")
        print(f"📧 Email: admin@pharmacie-manager.com")
        print(f"👤 Username: admin")
        print(f"🔑 Password: admin123")
        print("\n⚠️  IMPORTANT: Changez le mot de passe après la première connexion!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur lors de l'initialisation: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
