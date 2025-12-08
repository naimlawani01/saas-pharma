# Création d'un Super Administrateur

Ce script permet de créer un super administrateur pour l'application Pharmacie Manager.

## Utilisation sur Railway

### Option 1 : Via les variables d'environnement (Recommandé)

1. Dans votre projet Railway, allez dans **Variables**
2. Ajoutez ces variables d'environnement (optionnelles, valeurs par défaut ci-dessous) :
   ```
   SUPERADMIN_USERNAME=superadmin
   SUPERADMIN_EMAIL=admin@pharmaciemanager.com
   SUPERADMIN_PASSWORD=superadmin123
   SUPERADMIN_FULL_NAME=Super Administrateur
   ```
3. Le script s'exécutera automatiquement au démarrage du conteneur (déjà configuré dans le Dockerfile)

### Option 2 : Exécution manuelle via Railway CLI

1. Connectez-vous à votre conteneur Railway :
   ```bash
   railway run bash
   ```

2. Exécutez le script :
   ```bash
   python scripts/create_superadmin.py
   ```

### Option 3 : Exécution manuelle avec variables personnalisées

```bash
railway run bash
```

Puis dans le conteneur :
```bash
export SUPERADMIN_USERNAME="monadmin"
export SUPERADMIN_EMAIL="admin@example.com"
export SUPERADMIN_PASSWORD="MotDePasseSecurise123!"
export SUPERADMIN_FULL_NAME="Mon Nom"
python scripts/create_superadmin.py
```

## Utilisation en local

```bash
cd backend
python scripts/create_superadmin.py
```

Ou avec des variables personnalisées :
```bash
export SUPERADMIN_USERNAME="monadmin"
export SUPERADMIN_EMAIL="admin@example.com"
export SUPERADMIN_PASSWORD="MotDePasseSecurise123!"
export SUPERADMIN_FULL_NAME="Mon Nom"
python scripts/create_superadmin.py
```

## Comportement

- Le script vérifie d'abord si un super admin existe déjà
- Si un super admin existe, il affiche un message et ne fait rien
- Si un utilisateur avec le même username/email existe, il le met à jour en super admin
- Sinon, il crée un nouveau super admin

## Sécurité

⚠️ **IMPORTANT** : Changez le mot de passe par défaut après la première connexion !

Le super admin créé :
- N'est **pas** associé à une pharmacie (`pharmacy_id = None`)
- A accès au panneau d'administration global (`/admin`)
- Peut gérer toutes les pharmacies du système

