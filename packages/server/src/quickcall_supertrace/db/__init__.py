"""
Database module for SuperTrace.

Provides SQLite storage with async support via aiosqlite.

Related: schema.py (table definitions), client.py (CRUD operations)
"""

from .client import Database, get_db
from .schema import init_db

__all__ = ["Database", "get_db", "init_db"]
