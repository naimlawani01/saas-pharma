from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Importer le logging DB pour activer les listeners
from app.db.logging import *  # noqa: F401, F403

# psycopg2-binary est utilisé (version 2.9.11+ avec support Python 3.14)
# SQLAlchemy 2.0 supporte psycopg2 par défaut avec postgresql://
database_url = settings.DATABASE_URL

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency pour obtenir une session de base de données."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
