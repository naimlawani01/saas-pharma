from fastapi import FastAPI, Request
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
