"""
Configuration du logging pour les opérations de base de données.
"""

import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from app.core.logging import db_logger


@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log les requêtes SQL avant exécution."""
    db_logger.debug(
        "SQL query",
        extra={
            "extra_data": {
                "statement": statement,
                "parameters": parameters if parameters else None,
                "executemany": executemany,
            }
        }
    )


@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log les résultats des requêtes SQL."""
    db_logger.debug(
        "SQL query executed",
        extra={
            "extra_data": {
                "statement": statement,
                "rowcount": cursor.rowcount if cursor else None,
            }
        }
    )


@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log les nouvelles connexions à la base de données."""
    db_logger.info(
        "Database connection established",
        extra={
            "extra_data": {
                "connection_id": id(dbapi_conn),
            }
        }
    )


@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log les checkouts de connexions."""
    db_logger.debug(
        "Database connection checked out",
        extra={
            "extra_data": {
                "connection_id": id(dbapi_conn),
            }
        }
    )


@event.listens_for(Pool, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log les checkins de connexions."""
    db_logger.debug(
        "Database connection checked in",
        extra={
            "extra_data": {
                "connection_id": id(dbapi_conn),
            }
        }
    )

