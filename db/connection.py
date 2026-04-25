"""
Подключение к PostgreSQL (Supabase) через SQLAlchemy.

Использует DATABASE_URL из .env для создания engine и сессий.
"""

import logging
import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from db.models import Base

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

# Получение DATABASE_URL из .env
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL не найден в .env файле. "
        "Добавьте строку подключения к PostgreSQL."
    )

# Создание engine с connection pooling
# Для Supabase pooler используем минимальные настройки
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    pool_pre_ping=False,  # Отключаем pre-ping
)

# Создание фабрики сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    Event listener для настройки соединения.
    Для PostgreSQL можно добавить SET команды при необходимости.
    """
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency для получения сессии БД.
    
    Использование:
        with get_db() as db:
            # работа с БД
            pass
    
    Yields:
        Session: SQLAlchemy сессия
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка при работе с БД: {e}")
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Создание всех таблиц в БД.
    
    ВНИМАНИЕ: Используйте Alembic для миграций в продакшене!
    Эта функция для быстрого старта и тестирования.
    """
    logger.info("Создание таблиц в БД...")
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы успешно созданы")


def drop_all_tables() -> None:
    """
    ОПАСНО: Удаление всех таблиц из БД.
    Используйте только для разработки!
    """
    logger.warning("ВНИМАНИЕ: Удаление всех таблиц из БД!")
    Base.metadata.drop_all(bind=engine)
    logger.info("Все таблицы удалены")


def test_connection() -> bool:
    """
    Проверка подключения к БД.
    
    Returns:
        bool: True если подключение успешно
    """
    try:
        # Используем прямое подключение через psycopg2 для проверки
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        logger.info("✓ Подключение к БД успешно")
        return True
    except Exception as e:
        logger.error(f"✗ Ошибка подключения к БД: {e}")
        return False


if __name__ == "__main__":
    # Тестирование подключения
    logging.basicConfig(level=logging.INFO)
    
    print("Проверка подключения к PostgreSQL...")
    if test_connection():
        print("\n✓ Подключение успешно!")
        print(f"Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'hidden'}")
    else:
        print("\n✗ Не удалось подключиться к БД")
        print("Проверьте DATABASE_URL в .env файле")
