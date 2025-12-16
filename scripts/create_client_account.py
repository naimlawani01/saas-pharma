#!/usr/bin/env python3
"""
Script pour créer un compte client (pharmacie + admin)

Usage:
    python scripts/create_client_account.py

Ce script crée:
1. Une pharmacie avec les infos du client
2. Un compte admin pour cette pharmacie
3. Génère les identifiants de connexion
"""

import os
import sys
from pathlib import Path
import secrets
import string

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import SessionLocal
from app.models.user import User
from app.models.pharmacy import Pharmacy
from app.core.security import get_password_hash


def generate_password(length=12):
    """Génère un mot de passe sécurisé"""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_client_account():
    print("=" * 60)
    print("🏥 CRÉATION D'UN COMPTE CLIENT")
    print("=" * 60)
    
    # Collecter les informations
    print("\n📝 Informations de la pharmacie:")
    pharmacy_name = input("   Nom de la pharmacie: ").strip()
    pharmacy_address = input("   Adresse: ").strip()
    pharmacy_city = input("   Ville: ").strip()
    pharmacy_phone = input("   Téléphone: ").strip()
    pharmacy_email = input("   Email de la pharmacie: ").strip()
    pharmacy_license = input("   Numéro de licence: ").strip()
    
    print("\n👤 Informations de l'administrateur:")
    admin_name = input("   Nom complet: ").strip()
    admin_email = input("   Email (pour connexion): ").strip()
    admin_username = input("   Nom d'utilisateur: ").strip()
    
    # Générer ou demander un mot de passe
    use_generated = input("   Générer un mot de passe automatique? (O/n): ").strip().lower()
    if use_generated != 'n':
        admin_password = generate_password()
        print(f"   Mot de passe généré: {admin_password}")
    else:
        admin_password = input("   Mot de passe: ").strip()
    
    # Confirmation
    print("\n" + "-" * 60)
    print("📋 RÉCAPITULATIF:")
    print(f"   Pharmacie: {pharmacy_name}")
    print(f"   Adresse: {pharmacy_address}, {pharmacy_city}")
    print(f"   Admin: {admin_name} ({admin_email})")
    print("-" * 60)
    
    confirm = input("\n✅ Confirmer la création? (O/n): ").strip().lower()
    if confirm == 'n':
        print("❌ Création annulée")
        return
    
    # Créer dans la base de données
    db = SessionLocal()
    try:
        # Vérifier si la pharmacie existe déjà
        existing_pharmacy = db.query(Pharmacy).filter(
            Pharmacy.license_number == pharmacy_license
        ).first()
        
        if existing_pharmacy:
            print(f"⚠️  Une pharmacie avec ce numéro de licence existe déjà: {existing_pharmacy.name}")
            return
        
        # Vérifier si l'email admin existe déjà
        existing_user = db.query(User).filter(User.email == admin_email).first()
        if existing_user:
            print(f"⚠️  Un utilisateur avec cet email existe déjà")
            return
        
        # Créer la pharmacie
        pharmacy = Pharmacy(
            name=pharmacy_name,
            address=pharmacy_address,
            city=pharmacy_city,
            phone=pharmacy_phone,
            email=pharmacy_email,
            license_number=pharmacy_license,
            is_active=True
        )
        db.add(pharmacy)
        db.commit()
        db.refresh(pharmacy)
        
        print(f"\n✅ Pharmacie créée (ID: {pharmacy.id})")
        
        # Créer l'admin
        admin = User(
            email=admin_email,
            username=admin_username,
            full_name=admin_name,
            hashed_password=get_password_hash(admin_password),
            role="admin",
            pharmacy_id=pharmacy.id,
            is_active=True,
            is_superuser=False  # Pas super admin, juste admin de sa pharmacie
        )
        db.add(admin)
        db.commit()
        
        print(f"✅ Administrateur créé")
        
        # Afficher les informations de connexion
        print("\n" + "=" * 60)
        print("🎉 COMPTE CLIENT CRÉÉ AVEC SUCCÈS!")
        print("=" * 60)
        print("\n📧 INFORMATIONS DE CONNEXION À ENVOYER AU CLIENT:")
        print("-" * 60)
        print(f"   URL de l'application: [URL de votre serveur]")
        print(f"   Email: {admin_email}")
        print(f"   Mot de passe: {admin_password}")
        print(f"   Pharmacie ID: {pharmacy.id}")
        print("-" * 60)
        print("\n⚠️  IMPORTANT: Demandez au client de changer son mot de passe")
        print("   après la première connexion!")
        
        # Sauvegarder dans un fichier (optionnel)
        save_file = input("\n💾 Sauvegarder les infos dans un fichier? (O/n): ").strip().lower()
        if save_file != 'n':
            filename = f"client_{admin_username}_{pharmacy.id}.txt"
            with open(filename, 'w') as f:
                f.write(f"=== INFORMATIONS CLIENT ===\n")
                f.write(f"Date de création: {pharmacy.created_at}\n\n")
                f.write(f"PHARMACIE:\n")
                f.write(f"  ID: {pharmacy.id}\n")
                f.write(f"  Nom: {pharmacy_name}\n")
                f.write(f"  Adresse: {pharmacy_address}, {pharmacy_city}\n")
                f.write(f"  Téléphone: {pharmacy_phone}\n")
                f.write(f"  Email: {pharmacy_email}\n")
                f.write(f"  Licence: {pharmacy_license}\n\n")
                f.write(f"ADMINISTRATEUR:\n")
                f.write(f"  Nom: {admin_name}\n")
                f.write(f"  Email: {admin_email}\n")
                f.write(f"  Username: {admin_username}\n")
                f.write(f"  Mot de passe: {admin_password}\n")
            print(f"✅ Informations sauvegardées dans: {filename}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    create_client_account()

