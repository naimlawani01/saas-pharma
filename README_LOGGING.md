# Système de Logging

Ce document décrit le système de logging implémenté pour l'API Pharmacie Manager.

## Structure

Le système de logging est organisé en plusieurs fichiers :

- `app/core/logging.py` : Configuration principale du logging
- `app/core/middleware.py` : Middleware pour le logging HTTP
- `app/core/exceptions.py` : Gestionnaires d'exceptions avec logging
- `app/db/logging.py` : Logging pour les opérations de base de données

## Fichiers de logs

Les logs sont enregistrés dans le répertoire `logs/` :

- `app.log` : Tous les logs de l'application (niveau INFO et supérieur)
- `errors.log` : Uniquement les erreurs (niveau ERROR et supérieur)
- `http.log` : Toutes les requêtes HTTP
- `database.log` : Toutes les opérations de base de données
- `validation.log` : Erreurs de validation Pydantic

## Format des logs

### Mode développement
- Format coloré et lisible dans la console
- Format : `[LEVEL] timestamp - logger - function:line - message`

### Mode production
- Format JSON structuré pour faciliter le parsing
- Format :
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "level": "INFO",
  "logger": "http",
  "message": "Request completed",
  "module": "middleware",
  "function": "dispatch",
  "line": 45,
  "extra_data": {
    "method": "GET",
    "path": "/api/v1/products",
    "status_code": 200,
    "process_time": 0.123
  }
}
```

## Types de logs

### 1. Logs HTTP
Toutes les requêtes HTTP sont loggées avec :
- Méthode HTTP
- Chemin de la requête
- IP du client
- User-Agent
- Utilisateur authentifié (si applicable)
- Code de statut de la réponse
- Temps de traitement
- Paramètres de requête

**Exemple :**
```python
from app.core.logging import http_logger

http_logger.info("Custom HTTP log", extra={
    "extra_data": {
        "custom_field": "value"
    }
})
```

### 2. Logs de validation
Les erreurs de validation Pydantic sont automatiquement loggées avec :
- Chemin de la requête
- Erreurs de validation détaillées
- Corps de la requête (si disponible)

### 3. Logs de base de données
Les opérations SQL sont loggées avec :
- Requête SQL
- Paramètres
- Nombre de lignes affectées
- Connexions/checkouts de pool

**Exemple :**
```python
from app.core.logging import db_logger

db_logger.info("Custom DB operation", extra={
    "extra_data": {
        "operation": "create_product",
        "product_id": 123
    }
})
```

### 4. Logs d'erreurs
Toutes les exceptions sont loggées avec :
- Type d'erreur
- Message d'erreur
- Stack trace complète
- Contexte de la requête

## Utilisation dans le code

### Logger standard
```python
import logging

logger = logging.getLogger(__name__)

logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)  # Avec stack trace
```

### Logger avec données supplémentaires
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

logger.info(
    "Operation completed",
    extra={
        "extra_data": {
            "user_id": 123,
            "operation": "create_sale",
            "sale_id": 456
        }
    }
)
```

### Logger spécialisé
```python
from app.core.logging import http_logger, db_logger, validation_logger

# Log HTTP
http_logger.info("Custom HTTP event", extra={"extra_data": {...}})

# Log DB
db_logger.info("Custom DB event", extra={"extra_data": {...}})

# Log validation
validation_logger.warning("Validation issue", extra={"extra_data": {...}})
```

## Configuration

Le niveau de logging est configuré via la variable d'environnement `ENVIRONMENT` :

- `development` : DEBUG (logs détaillés, format coloré)
- `production` : INFO (logs essentiels, format JSON)

Dans `app/core/config.py` :
```python
ENVIRONMENT: str = "development"  # development, production, staging
```

## Rotation des logs

Pour la production, il est recommandé d'utiliser un outil de rotation des logs comme `logrotate` ou d'intégrer avec un service de logging externe (Datadog, Sentry, etc.).

## Exemples de logs

### Requête HTTP réussie
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "level": "INFO",
  "logger": "http",
  "message": "Request completed",
  "extra_data": {
    "method": "GET",
    "path": "/api/v1/products",
    "status_code": 200,
    "process_time": 0.123,
    "user_id": 1,
    "user_email": "admin@example.com"
  }
}
```

### Erreur de validation
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "level": "WARNING",
  "logger": "validation",
  "message": "Validation error",
  "extra_data": {
    "method": "POST",
    "path": "/api/v1/products",
    "errors": [
      {
        "loc": ["body", "name"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
}
```

### Erreur de base de données
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "level": "ERROR",
  "logger": "database",
  "message": "Database error",
  "exception": "Traceback...",
  "extra_data": {
    "method": "POST",
    "path": "/api/v1/products",
    "error_type": "IntegrityError",
    "error_message": "duplicate key value violates unique constraint"
  }
}
```

## Intégration avec des services externes

Pour intégrer avec des services comme Sentry, Datadog, ou CloudWatch, vous pouvez ajouter des handlers personnalisés dans `app/core/logging.py`.

