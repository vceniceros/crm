"""Database exports for the CRM backend."""

from crm_backend.db.base import Base
from crm_backend.db.session import SessionLocal, engine, get_db_session, is_sqlite_database

__all__ = ["Base", "SessionLocal", "engine", "get_db_session", "is_sqlite_database"]
