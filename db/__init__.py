"""
Инициализация пакета db.

Экспортирует основные компоненты для удобного импорта.
Если DATABASE_URL не задан — модели всё равно доступны,
но engine/SessionLocal будут None.
"""

from db.models import Base, Region, Customer, Lot
from db.connection import (
    engine,
    SessionLocal,
    get_db,
    init_db,
    drop_all_tables,
    test_connection,
)

__all__ = [
    # Models
    "Base",
    "Region",
    "Customer",
    "Lot",
    # Connection
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "drop_all_tables",
    "test_connection",
]
