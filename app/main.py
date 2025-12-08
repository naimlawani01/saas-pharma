from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import HTTPLoggingMiddleware
from app.core.exceptions import (
    validation_exception_handler,
    sqlalchemy_exception_handler,
    general_exception_handler,
)
from app.api.v1 import api_router
from app.db.base import Base, engine

# Configurer le logging
setup_logging(environment=settings.ENVIRONMENT)

# Logger de test pour vérifier que le logging fonctionne
import logging
logger = logging.getLogger(__name__)
logger.info("=" * 60)
logger.info(f"🚀 Démarrage de {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
logger.info(f"📝 Environnement: {settings.ENVIRONMENT}")
logger.info(f"🔧 Debug: {settings.DEBUG}")
logger.info("=" * 60)

# Créer les tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middlewares
# 1. Middleware pour le logging HTTP (doit être en premier pour capturer toutes les requêtes)
app.add_middleware(HTTPLoggingMiddleware)

# 3. Middleware pour le protocole HTTPS (Railway)
@app.middleware("http")
async def forwarded_proto_middleware(request: Request, call_next):
    """
    Empêche Railway de rediriger en HTTP en disant à FastAPI :
    'Cette requête est réellement en HTTPS'
    
    Railway passe l'en-tête x-forwarded-proto pour indiquer le protocole réel
    utilisé par le client (HTTPS), même si la connexion interne est en HTTP.
    """
    if request.headers.get("x-forwarded-proto") == "https":
        request.scope["scheme"] = "https"
    return await call_next(request)

# 4. CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Handlers d'exceptions
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Inclure les routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    """Point d'entrée de l'API."""
    return {
        "message": "Pharmacie Manager API",
        "version": settings.PROJECT_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Vérification de santé de l'API."""
    return {"status": "healthy"}
