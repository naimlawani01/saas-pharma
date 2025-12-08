#!/usr/bin/env python3
"""
Script de démarrage pour l'application FastAPI.
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    # Désactiver le logging par défaut d'uvicorn pour utiliser notre système
    # Le logging sera configuré dans app.main via setup_logging()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_config=None,  # Désactiver la config par défaut d'uvicorn
        use_colors=False,  # On utilise nos propres couleurs
    )
