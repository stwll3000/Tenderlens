"""
Подключение к PostgreSQL (Supabase) через SQLAlchemy.

Использует DATABASE_URL из .env для создания engine и сессий.
Если DATABASE_URL не задан — модуль загружается без ошибок,
но engine/SessionLocal будут None. Это позволяет импортировать
модели и аналитику без настроенной БД.
"""

import logging
import os
import warnings
from typing import Generator, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
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

# Graceful degradation: без DATABASE_URL модуль работает, но БД-функции недоступны
engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None

if DATABASE_URL:
    # Создание engine для Supabase Transaction Pooler
    # Transaction pooler работает в режиме pgbouncer transaction mode
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,  # Не используем pool, т.к. pooler сам управляет
        echo=False,
        pool_pre_ping=True,  # Проверка соединения перед использованием
        connect_args={
            "connect_timeout": 10,
        }
    )

    # Создание фабрики сессий
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,
    )
else:
    warnings.warn(
        "DATABASE_URL не задан в .env файле. "
        "БД-функции недоступны. Аналитика и модели работают без БД.",
        stacklevel=2,
    )


def _require_db():
    """Проверка, что БД сконфигурирована. Вызывать перед БД-операциями."""
    if engine is None or SessionLocal is None:
        raise RuntimeError(
            "DATABASE_URL не задан. Для работы с БД создайте .env файл "
            "с DATABASE_URL=postgresql://... (см. .env.example)"
        )


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
    _require_db()
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
    _require_db()
    logger.info("Создание таблиц в БД...")
    Base.metadata.create_all(bind=engine)
    logger.info("Таблицы успешно созданы")


def drop_all_tables() -> None:
    """
    ОПАСНО: Удаление всех таблиц из БД.
    Используйте только для разработки!
    """
    _require_db()
    logger.warning("ВНИМАНИЕ: Удаление всех таблиц из БД!")
    Base.metadata.drop_all(bind=engine)
    logger.info("Все таблицы удалены")


def test_connection() -> bool:
    """
    Проверка подключения к БД.

    Returns:
        bool: True если подключение успешно
    """
    if engine is None:
        logger.error("✗ DATABASE_URL не задан")
        return False
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✓ Подключение к БД успешно: {version}")
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
        print(f"Database URL: {DATABASE_URL.split('@')[1] if DATABASE_URL and '@' in DATABASE_URL else 'hidden'}")
    else:
        print("\n✗ Не удалось подключиться к БД")
        print("Проверьте DATABASE_URL в .env файле")
