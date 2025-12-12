"""
Middlewares pour le logging HTTP et la gestion des erreurs.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import http_logger

logger = logging.getLogger(__name__)


class HTTPLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware pour logger toutes les requêtes HTTP."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Informations de la requête
        start_time = time.time()
        method = request.method
        url = str(request.url)
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Récupérer l'utilisateur si authentifié
        user_id = None
        user_email = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
            user_email = getattr(request.state.user, "email", None)
        
        # Logger la requête entrante
        http_logger.info(
            "Request received",
            extra={
                "extra_data": {
                    "method": method,
                    "path": path,
                    "url": url,
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "user_id": user_id,
                    "user_email": user_email,
                    "query_params": dict(request.query_params),
                }
            }
        )
        
        # Exécuter la requête
        try:
            response = await call_next(request)
            
            # Calculer le temps de traitement
            process_time = time.time() - start_time
            
            # Informations de la réponse
            status_code = response.status_code
            
            # Logger la réponse avec le bon niveau
            if status_code >= 500:
                log_level = logging.ERROR
                status_emoji = "❌"
            elif status_code >= 400:
                log_level = logging.ERROR if status_code == 422 else logging.WARNING
                status_emoji = "⚠️" if status_code != 422 else "❌"
            else:
                log_level = logging.INFO
                status_emoji = "✅"
            
            # Récupérer le body de la réponse si c'est une erreur
            response_body = None
            if status_code >= 400:
                try:
                    # Pour les erreurs, on veut voir le contenu de la réponse
                    # Mais on ne peut pas lire le body ici car il a déjà été envoyé
                    # On va juste logger le status code et le path
                    pass
                except:
                    pass
            
            # Message plus descriptif
            if status_code >= 500:
                message = f"{status_emoji} Server Error ({status_code}) - {method} {path}"
            elif status_code >= 400:
                message = f"{status_emoji} Client Error ({status_code}) - {method} {path}"
            else:
                message = f"{status_emoji} {method} {path} - {status_code}"
            
            http_logger.log(
                log_level,
                message,
                extra={
                    "extra_data": {
                        "method": method,
                        "path": path,
                        "status_code": status_code,
                        "process_time": round(process_time, 3),
                        "user_id": user_id,
                        "user_email": user_email,
                    }
                }
            )
            
            # Ajouter le temps de traitement dans les headers
            response.headers["X-Process-Time"] = str(round(process_time, 3))
            
            return response
            
        except Exception as e:
            # Calculer le temps de traitement
            process_time = time.time() - start_time
            
            # Logger l'erreur avec TOUS les détails
            logger.error(
                f"❌ Request Failed (500) - {method} {path}\n"
                f"Error: {type(e).__name__}: {str(e)}\n"
                f"URL: {url}\n"
                f"Query params: {dict(request.query_params)}\n"
                f"User: {user_email} (ID: {user_id})\n"
                f"Client IP: {client_ip}",
                exc_info=True,
                extra={
                    "extra_data": {
                        "method": method,
                        "path": path,
                        "url": url,
                        "query_params": dict(request.query_params),
                        "process_time": round(process_time, 3),
                        "user_id": user_id,
                        "user_email": user_email,
                        "client_ip": client_ip,
                        "user_agent": user_agent,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "status_code": 500,
                    }
                }
            )
            
            # Logger aussi dans le logger HTTP
            http_logger.error(
                f"Request failed - {method} {path}",
                exc_info=True,
                extra={
                    "extra_data": {
                        "method": method,
                        "path": path,
                        "url": url,
                        "query_params": dict(request.query_params),
                        "process_time": round(process_time, 3),
                        "user_id": user_id,
                        "user_email": user_email,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "status_code": 500,
                    }
                }
            )
            
            raise



