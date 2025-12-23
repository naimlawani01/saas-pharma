"""
Gestionnaires d'exceptions personnalisés pour FastAPI.
"""

import logging
from typing import Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DatabaseError
from pydantic import ValidationError

from app.core.logging import validation_logger, db_logger

logger = logging.getLogger(__name__)


def make_json_serializable(obj: Any) -> Any:
    """
    Convertit les objets non-sérialisables en JSON (bytes, etc.) en strings.
    """
    if isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            return str(obj)
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(make_json_serializable(item) for item in obj)
    return obj


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Gère les erreurs de validation Pydantic.
    """
    # Nettoyer les erreurs pour les rendre sérialisables en JSON
    errors = make_json_serializable(exc.errors())
    
    # Formater les erreurs de manière lisible
    error_details = []
    for error in errors:
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        error_type = error.get("type", "unknown")
        error_msg = error.get("msg", "Validation error")
        error_details.append(f"  • {field}: {error_msg} (type: {error_type})")
    
    error_summary = "\n".join(error_details)
    
    # Nettoyer le body pour les logs
    body_content = make_json_serializable(exc.body) if hasattr(exc, 'body') else None
    
    # Logger les erreurs de validation avec plus de détails
    logger.error(
        f"❌ Validation Error (422) - {request.method} {request.url.path}\n"
        f"Erreurs de validation:\n{error_summary}\n"
        f"Body reçu: {body_content if body_content else 'N/A'}",
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "status_code": 422,
                "errors": errors,
                "body": body_content,
            }
        }
    )
    
    # Logger aussi dans le logger de validation
    validation_logger.error(
        f"Validation error - {request.method} {request.url.path}",
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "status_code": 422,
                "errors": errors,
                "error_summary": error_summary,
                "body": body_content,
            }
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Erreur de validation",
            "errors": errors,
        }
    )


async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError
) -> JSONResponse:
    """
    Gère les erreurs de base de données SQLAlchemy.
    """
    error_type = type(exc).__name__
    error_message = str(exc)
    
    # Récupérer le body de la requête si possible
    request_body = None
    try:
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            if body:
                import json
                try:
                    request_body = json.loads(body.decode())
                except:
                    request_body = body.decode()[:500]  # Limiter à 500 caractères
    except:
        pass
    
    # Logger l'erreur de base de données avec TOUS les détails
    logger.error(
        f"❌ Database Error (500) - {request.method} {request.url.path}\n"
        f"Type: {error_type}\n"
        f"Message: {error_message}\n"
        f"URL: {request.url}\n"
        f"Query params: {dict(request.query_params)}\n"
        f"Request body: {request_body}",
        exc_info=True,
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "url": str(request.url),
                "query_params": dict(request.query_params),
                "request_body": request_body,
                "error_type": error_type,
                "error_message": error_message,
                "status_code": 500,
            }
        }
    )
    
    # Logger aussi dans le logger de base de données
    db_logger.error(
        f"Database error - {request.method} {request.url.path}",
        exc_info=True,
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "url": str(request.url),
                "query_params": dict(request.query_params),
                "request_body": request_body,
                "error_type": error_type,
                "error_message": error_message,
                "status_code": 500,
            }
        }
    )
    
    # Messages d'erreur selon le type
    if isinstance(exc, IntegrityError):
        # Analyser le message d'erreur pour identifier le champ en cause
        error_message_lower = error_message.lower()
        
        # Détecter les erreurs de contrainte UNIQUE
        if 'unique' in error_message_lower or 'duplicate' in error_message_lower:
            # Identifier le champ concerné
            if 'barcode' in error_message_lower:
                user_message = "Ce code-barres existe déjà. Veuillez en utiliser un autre."
            elif 'sku' in error_message_lower:
                user_message = "Ce SKU existe déjà. Veuillez en utiliser un autre."
            elif 'sync_id' in error_message_lower:
                user_message = "Cette référence de synchronisation existe déjà."
            elif 'license_number' in error_message_lower:
                user_message = "Ce numéro de licence existe déjà."
            elif 'email' in error_message_lower:
                user_message = "Cet email existe déjà."
            elif 'username' in error_message_lower:
                user_message = "Ce nom d'utilisateur existe déjà."
            else:
                # Message générique mais plus informatif
                user_message = "Cette valeur existe déjà dans la base de données. Veuillez vérifier les champs uniques (code-barres, SKU, etc.)."
        else:
            # Autre type d'erreur d'intégrité (foreign key, etc.)
            user_message = "Erreur d'intégrité des données. Vérifiez que les données sont valides."
    elif isinstance(exc, DatabaseError):
        user_message = "Erreur de base de données. Veuillez réessayer plus tard."
    else:
        user_message = "Une erreur de base de données s'est produite."
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST if isinstance(exc, IntegrityError) else status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": user_message,
            "error_type": error_type,
        }
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Gère toutes les autres exceptions non gérées.
    """
    error_type = type(exc).__name__
    error_message = str(exc)
    
    # Récupérer le body de la requête si possible
    request_body = None
    try:
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            if body:
                import json
                try:
                    request_body = json.loads(body.decode())
                except:
                    request_body = body.decode()[:500]  # Limiter à 500 caractères
    except:
        pass
    
    # Récupérer les headers importants
    headers_info = {
        "content-type": request.headers.get("content-type"),
        "authorization": "Bearer ***" if request.headers.get("authorization") else None,
        "user-agent": request.headers.get("user-agent"),
    }
    
    # Logger l'erreur avec TOUS les détails
    logger.error(
        f"❌ Unhandled Exception (500) - {request.method} {request.url.path}\n"
        f"Type: {error_type}\n"
        f"Message: {error_message}\n"
        f"URL: {request.url}\n"
        f"Query params: {dict(request.query_params)}\n"
        f"Headers: {headers_info}\n"
        f"Request body: {request_body}",
        exc_info=True,
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "url": str(request.url),
                "query_params": dict(request.query_params),
                "headers": headers_info,
                "request_body": request_body,
                "error_type": error_type,
                "error_message": error_message,
                "status_code": 500,
            }
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Une erreur interne s'est produite. Veuillez contacter l'administrateur.",
            "error_type": error_type,
        }
    )

