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

# Copier le code backend
COPY . .

# Copier Alembic
COPY alembic ./alembic
COPY alembic.ini .

# Port exposé par l'app
EXPOSE 8000

# Lancer les migrations puis démarrer l'API
# Railway fournit $PORT ; fallback 8000 en local
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

