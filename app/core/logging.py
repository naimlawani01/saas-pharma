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
    
    def format(self, record: logging.LogRecord) -> str:
        log_color = self.COLORS.get(record.levelname, "")
        reset = self.RESET
        
        # Format avec couleurs
        log_format = (
            f"{log_color}[{record.levelname:8}]{reset} "
            f"{record.asctime} - {record.name} - {record.funcName}:{record.lineno} - "
            f"{log_color}{record.getMessage()}{reset}"
        )
        
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
    console_handler.setLevel(log_level)
    
    if environment == "development":
        console_formatter = ColoredFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        console_formatter = JSONFormatter()
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
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
    
    # Réduire le bruit des loggers externes
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


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

