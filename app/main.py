from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router
from app.db.base import Base, engine

# Créer les tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Note: Railway gère déjà HTTPS en amont, donc pas besoin de middleware de redirection
# Le middleware ForceHTTPSMiddleware a été supprimé car il causait des redirections 307
# qui créaient des problèmes de Mixed Content entre Vercel (HTTPS) et Railway (HTTPS)

# CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
