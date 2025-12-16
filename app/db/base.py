from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Importer le logging DB pour activer les listeners
from app.db.logging import *  # noqa: F401, F403

# psycopg2-binary est utilisé pour PostgreSQL
# SQLite est utilisé en mode local/Electron
database_url = settings.DATABASE_URL

# Déterminer si on utilise SQLite ou PostgreSQL
is_sqlite = database_url.startswith('sqlite')

if is_sqlite:
    # SQLite ne supporte pas pool_size et max_overflow
    # check_same_thread=False permet l'utilisation multi-thread
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
    
    # Activer les foreign keys pour SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # PostgreSQL avec pool de connexions
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
