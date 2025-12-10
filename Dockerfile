# Dockerfile pour déployer le backend FastAPI sur Railway
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dépendances système (pour psycopg / compilation éventuelle)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code backend (inclut déjà alembic et alembic.ini)
COPY . .

# Port exposé par l'app
EXPOSE 8000

# Lancer les migrations, créer le super admin (si besoin), puis démarrer l'API
# Railway fournit $PORT ; fallback 8000 en local
# Pour créer le super admin, définissez les variables d'environnement :
# SUPERADMIN_USERNAME, SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD, SUPERADMIN_FULL_NAME
CMD ["sh", "-c", "set -e && echo '🔄 Exécution des migrations...' && alembic upgrade head && echo '✅ Migrations terminées' && (python scripts/create_superadmin.py || echo '⚠️  Échec création super admin, continuation...') && echo '🚀 Démarrage de l\'API...' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

