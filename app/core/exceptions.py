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


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Gère les erreurs de validation Pydantic.
    """
    errors = exc.errors()
    
    # Logger les erreurs de validation
    validation_logger.warning(
        "Validation error",
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "errors": errors,
                "body": exc.body if hasattr(exc, "body") else None,
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
    
    # Logger l'erreur de base de données
    db_logger.error(
        "Database error",
        exc_info=True,
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "error_type": error_type,
                "error_message": error_message,
            }
        }
    )
    
    # Messages d'erreur selon le type
    if isinstance(exc, IntegrityError):
        user_message = "Erreur d'intégrité des données. Vérifiez que les données sont valides."
    elif isinstance(exc, DatabaseError):
        user_message = "Erreur de base de données. Veuillez réessayer plus tard."
    else:
        user_message = "Une erreur de base de données s'est produite."
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    
    # Logger l'erreur
    logger.error(
        "Unhandled exception",
        exc_info=True,
        extra={
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "error_type": error_type,
                "error_message": error_message,
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

