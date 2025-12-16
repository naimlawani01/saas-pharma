#!/usr/bin/env python3
"""Script pour corriger l'email admin dans SQLite"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'pharmacie.db')

print(f"Base de données: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Voir les utilisateurs actuels
print("\n📋 Utilisateurs actuels:")
cursor.execute("SELECT id, email, username FROM users")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}, Email: {row[1]}, Username: {row[2]}")

# Corriger l'email
print("\n🔧 Correction de l'email...")
cursor.execute("""
    UPDATE users 
    SET email = 'admin@pharmacie-manager.com' 
    WHERE email = 'admin@pharmacie.local'
""")

rows_updated = cursor.rowcount
conn.commit()

print(f"  ✅ {rows_updated} ligne(s) mise(s) à jour")

# Vérifier
print("\n📋 Utilisateurs après correction:")
cursor.execute("SELECT id, email, username FROM users")
for row in cursor.fetchall():
    print(f"  ID: {row[0]}, Email: {row[1]}, Username: {row[2]}")

conn.close()

print("\n✅ Terminé! Tu peux te connecter avec:")
print("   Email: admin@pharmacie-manager.com")
print("   Mot de passe: admin123")

