"""
Database package - provides abstraction layer for MongoDB and SQLite
"""
from .abstraction import (
    DatabaseInterface,
    MongoDBDatabase,
    SQLiteDatabase,
    get_database,
    init_database,
    get_db,
    USE_SQLITE
)

__all__ = [
    'DatabaseInterface',
    'MongoDBDatabase', 
    'SQLiteDatabase',
    'get_database',
    'init_database',
    'get_db',
    'USE_SQLITE'
]
