# Pharmacie Manager - Backend API

Backend FastAPI pour le système SaaS de gestion de pharmacies multi-tenant avec support offline/online.

## 🚀 Fonctionnalités

- **Multi-pharmacies (Multi-tenant)** : Isolation complète des données par pharmacie
- **Authentification JWT** : Sécurisation des endpoints avec tokens
- **Gestion complète** :
  - Stock et produits
  - Ventes
  - Clients
  - Fournisseurs et commandes
  - Rapports
- **Synchronisation hybride** : Support offline/online avec résolution de conflits
- **API RESTful** : Documentation automatique avec Swagger/OpenAPI

## 📋 Prérequis

- Python 3.10+ (recommandé: 3.11 ou 3.12 pour une meilleure compatibilité)
- PostgreSQL 12+
- pip

> **Note** : Si vous utilisez Python 3.14 et rencontrez des problèmes avec `psycopg2-binary`, le projet utilise maintenant `psycopg` (version 3) qui est mieux supporté. Voir [INSTALLATION.md](./INSTALLATION.md) pour plus de détails.

## 🛠️ Installation

1. **Créer un environnement virtuel** :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

2. **Installer les dépendances** :
```bash
pip install -r requirements.txt
```

3. **Configurer les variables d'environnement** :
```bash
cp env.example .env
# Éditer .env avec vos paramètres
```

4. **Créer la base de données PostgreSQL** :
```sql
CREATE DATABASE pharmacie_manager;
```

5. **Initialiser la base de données** :
```bash
python scripts/init_db.py
```

## 🏃 Démarrage

```bash
python run.py
# ou
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

L'API sera accessible sur :
- API : http://localhost:8000
- Documentation Swagger : http://localhost:8000/docs
- Documentation ReDoc : http://localhost:8000/redoc

## 📚 Structure du projet

```
backend/
├── alembic/          # Migrations de base de données
├── app/              # Code source principal
│   ├── api/         # Routes API
│   │   └── v1/      # Version 1 de l'API
│   ├── core/        # Configuration et sécurité
│   ├── db/          # Configuration base de données
│   ├── models/      # Modèles SQLAlchemy
│   ├── schemas/     # Schémas Pydantic
│   └── main.py      # Point d'entrée FastAPI
├── scripts/         # Scripts utilitaires
├── alembic.ini      # Configuration Alembic
├── requirements.txt # Dépendances Python
├── env.example      # Exemple de variables d'environnement
└── run.py           # Script de démarrage
```

## 🔐 Authentification

L'API utilise JWT (JSON Web Tokens) pour l'authentification.

### Créer un utilisateur

```bash
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "username": "username",
  "password": "password",
  "full_name": "John Doe",
  "pharmacy_id": 1
}
```

### Se connecter

```bash
POST /api/v1/auth/login
# Utiliser OAuth2PasswordRequestForm
# username: email ou username
# password: mot de passe
```

### Utiliser le token

Ajouter le token dans les headers :
```
Authorization: Bearer <token>
```

## 📡 Endpoints principaux

### Authentification
- `POST /api/v1/auth/login` - Connexion
- `POST /api/v1/auth/register` - Inscription
- `GET /api/v1/auth/me` - Informations utilisateur
- `POST /api/v1/auth/refresh` - Rafraîchir le token

### Pharmacies
- `GET /api/v1/pharmacies` - Liste des pharmacies
- `POST /api/v1/pharmacies` - Créer une pharmacie
- `GET /api/v1/pharmacies/{id}` - Détails d'une pharmacie
- `PUT /api/v1/pharmacies/{id}` - Mettre à jour

### Produits
- `GET /api/v1/products` - Liste des produits
- `POST /api/v1/products` - Créer un produit
- `GET /api/v1/products/{id}` - Détails
- `PUT /api/v1/products/{id}` - Mettre à jour
- `DELETE /api/v1/products/{id}` - Supprimer

### Ventes
- `GET /api/v1/sales` - Liste des ventes
- `POST /api/v1/sales` - Créer une vente
- `GET /api/v1/sales/{id}` - Détails

### Clients
- `GET /api/v1/customers` - Liste des clients
- `POST /api/v1/customers` - Créer un client
- `GET /api/v1/customers/{id}` - Détails
- `PUT /api/v1/customers/{id}` - Mettre à jour
- `DELETE /api/v1/customers/{id}` - Supprimer

### Fournisseurs
- `GET /api/v1/suppliers` - Liste des fournisseurs
- `POST /api/v1/suppliers` - Créer un fournisseur
- `GET /api/v1/suppliers/orders` - Liste des commandes
- `POST /api/v1/suppliers/orders` - Créer une commande

### Synchronisation
- `POST /api/v1/sync` - Synchroniser les données
- `GET /api/v1/sync/logs` - Historique des synchronisations

## 🔄 Synchronisation

Le système supporte la synchronisation bidirectionnelle entre le client local et le cloud.

### Upload (Local → Cloud)
```json
POST /api/v1/sync
{
  "direction": "upload",
  "entity_types": ["products", "sales"],
  "last_sync_at": "2024-01-01T00:00:00Z"
}
```

### Download (Cloud → Local)
```json
POST /api/v1/sync
{
  "direction": "download",
  "entity_types": ["products", "sales"]
}
```

### Bidirectionnel
```json
POST /api/v1/sync
{
  "direction": "bidirectional",
  "entity_types": null  // Toutes les entités
}
```

## 🗄️ Base de données

Le projet utilise PostgreSQL avec SQLAlchemy ORM.

### Modèles principaux
- `User` - Utilisateurs
- `Pharmacy` - Pharmacies
- `Product` - Produits
- `Sale` / `SaleItem` - Ventes
- `Customer` - Clients
- `Supplier` / `SupplierOrder` - Fournisseurs
- `SyncLog` - Logs de synchronisation

## 🔒 Sécurité

- **JWT** : Tokens avec expiration
- **Multi-tenant** : Isolation des données par `pharmacy_id`
- **Permissions** : Rôles utilisateur (admin, pharmacist, assistant)
- **Validation** : Schémas Pydantic pour validation des données

## 🧪 Tests

```bash
# À venir
pytest
```

## 📝 Variables d'environnement

Voir `env.example` pour la liste complète des variables.

Variables importantes :
- `DATABASE_URL` - URL de connexion PostgreSQL
- `SECRET_KEY` - Clé secrète pour JWT
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Durée de vie des tokens

## 🚧 Prochaines étapes

- [ ] Migrations Alembic
- [ ] Tests unitaires et d'intégration
- [ ] Endpoints de rapports et statistiques
- [ ] Amélioration de la résolution de conflits
- [ ] Webhooks pour notifications
- [ ] Rate limiting
- [ ] Logging avancé

## 📄 Licence

Propriétaire - Tous droits réservés

## 👥 Support

Pour toute question ou problème, contactez l'équipe de développement.
