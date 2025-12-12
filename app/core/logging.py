"""
Configuration du système de logging pour l'API.
Gère les logs HTTP, erreurs de validation, base de données, etc.
"""

import logging
import sys
from pathlib import Path
from typing import Any
import json
from datetime import datetime

# Créer le répertoire logs s'il n'existe pas
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Formatter pour les logs en JSON structuré."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Ajouter les données supplémentaires si présentes
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        
        # Ajouter l'exception si présente
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Ajouter les attributs personnalisés
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info"
            ]:
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class ColoredFormatter(logging.Formatter):
    """Formatter avec couleurs pour la console (développement)."""
    
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    def __init__(self, datefmt=None):
        super().__init__(datefmt=datefmt)
        self.datefmt = datefmt or "%Y-%m-%d %H:%M:%S"
    
    def format(self, record: logging.LogRecord) -> str:
        # S'assurer que asctime est défini
        if not hasattr(record, 'asctime') or not record.asctime:
            record.asctime = self.formatTime(record, self.datefmt)
        
        log_color = self.COLORS.get(record.levelname, "")
        reset = self.RESET
        bold = self.BOLD
        
        # Format avec couleurs
        # Pour uvicorn, utiliser un format plus simple
        if record.name.startswith("uvicorn"):
            log_format = (
                f"{log_color}[{record.levelname:8}]{reset} "
                f"{record.getMessage()}"
            )
        else:
            # Format amélioré avec plus de détails pour les erreurs
            level_display = f"{bold}{log_color}[{record.levelname:8}]{reset}"
            
            # Pour les erreurs, afficher plus de détails
            if record.levelno >= logging.ERROR:
                log_format = (
                    f"{level_display} {record.asctime}\n"
                    f"  {bold}Module:{reset} {record.name}\n"
                    f"  {bold}Location:{reset} {record.funcName}:{record.lineno}\n"
                    f"  {bold}Message:{reset} {log_color}{record.getMessage()}{reset}"
                )
            else:
                log_format = (
                    f"{level_display} {record.asctime} - {record.name} - "
                    f"{record.funcName}:{record.lineno} - "
                    f"{log_color}{record.getMessage()}{reset}"
                )
        
        # Ajouter les données extra si présentes
        if hasattr(record, 'extra_data') and record.extra_data:
            extra_str = "\n  ".join(f"{k}: {v}" for k, v in record.extra_data.items())
            log_format += f"\n  {bold}Details:{reset}\n  {extra_str}"
        
        if record.exc_info:
            log_format += f"\n{self.formatException(record.exc_info)}"
        
        return log_format


def setup_logging(environment: str = "development") -> None:
    """
    Configure le système de logging.
    
    Args:
        environment: Environnement (development, production, etc.)
    """
    # Niveau de logging selon l'environnement
    log_level = logging.DEBUG if environment == "development" else logging.INFO
    
    # Logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Supprimer les handlers existants
    root_logger.handlers.clear()
    
    # Handler pour la console (avec couleurs en dev)
    console_handler = logging.StreamHandler(sys.stdout)
    # En développement, on veut voir tous les logs (DEBUG et plus)
    # En production, seulement INFO et plus
    console_handler.setLevel(logging.DEBUG if environment == "development" else logging.INFO)
    
    if environment == "development":
        console_formatter = ColoredFormatter(
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        console_formatter = JSONFormatter()
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # S'assurer que le logger racine utilise aussi le bon niveau
    root_logger.setLevel(logging.DEBUG if environment == "development" else logging.INFO)
    
    # Handler pour les fichiers (toujours en JSON)
    # Fichier général
    file_handler = logging.FileHandler(
        LOG_DIR / "app.log",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    # Fichier pour les erreurs uniquement
    error_handler = logging.FileHandler(
        LOG_DIR / "errors.log",
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)
    
    # Fichier pour les requêtes HTTP
    http_handler = logging.FileHandler(
        LOG_DIR / "http.log",
        encoding="utf-8"
    )
    http_handler.setLevel(logging.INFO)
    http_handler.setFormatter(JSONFormatter())
    http_logger = logging.getLogger("http")
    http_logger.addHandler(http_handler)
    http_logger.setLevel(logging.INFO)
    http_logger.propagate = False
    
    # Logger pour la base de données
    db_logger = logging.getLogger("database")
    db_handler = logging.FileHandler(
        LOG_DIR / "database.log",
        encoding="utf-8"
    )
    db_handler.setLevel(logging.INFO)
    db_handler.setFormatter(JSONFormatter())
    db_logger.addHandler(db_handler)
    db_logger.setLevel(logging.INFO)
    db_logger.propagate = False
    
    # Logger pour les validations
    validation_logger = logging.getLogger("validation")
    validation_handler = logging.FileHandler(
        LOG_DIR / "validation.log",
        encoding="utf-8"
    )
    validation_handler.setLevel(logging.WARNING)
    validation_handler.setFormatter(JSONFormatter())
    validation_logger.addHandler(validation_handler)
    validation_logger.setLevel(logging.WARNING)
    validation_logger.propagate = False
    
    # Configurer les loggers externes (ne pas les masquer complètement)
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(log_level)
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(console_handler)
    
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.setLevel(logging.INFO if environment == "development" else logging.WARNING)
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.addHandler(console_handler)
    
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.setLevel(log_level)
    uvicorn_error_logger.handlers.clear()
    uvicorn_error_logger.addHandler(console_handler)
    
    # SQLAlchemy - seulement les warnings en production
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(logging.WARNING if environment == "production" else logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Obtient un logger avec le nom spécifié.
    
    Args:
        name: Nom du logger (généralement __name__)
        
    Returns:
        Logger configuré
    """
    return logging.getLogger(name)


# Loggers spécialisés
http_logger = logging.getLogger("http")
db_logger = logging.getLogger("database")
validation_logger = logging.getLogger("validation")

