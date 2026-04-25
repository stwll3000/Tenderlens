"""
Скрипт для выгрузки данных из Supabase в JSON.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Настройка логирования для Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Connection strings для тестирования
CONNECTION_STRINGS = [
    # Session pooler (порт 5432)
    "postgresql://postgres.dnpjcxjjavzjmtfzlrip:1OSoLRpib7Tmd2Lu@aws-1-eu-north-1.pooler.supabase.com:5432/postgres",
    # Transaction pooler (порт 6543)
    "postgresql://postgres.dnpjcxjjavzjmtfzlrip:1OSoLRpib7Tmd2Lu@aws-1-eu-north-1.pooler.supabase.com:6543/postgres",
    # Попробуем aws-0 вместо aws-1
    "postgresql://postgres.dnpjcxjjavzjmtfzlrip:1OSoLRpib7Tmd2Lu@aws-0-eu-north-1.pooler.supabase.com:5432/postgres",
    "postgresql://postgres.dnpjcxjjavzjmtfzlrip:1OSoLRpib7Tmd2Lu@aws-0-eu-north-1.pooler.supabase.com:6543/postgres",
]


def export_table_to_json(engine, table_name: str, output_file: Path):
    """
    Выгружает таблицу из PostgreSQL в JSON.
    
    Args:
        engine: SQLAlchemy engine
        table_name: Имя таблицы
        output_file: Путь к выходному файлу
    """
    try:
        with engine.connect() as conn:
            # Получаем все данные из таблицы
            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            
            # Получаем названия колонок
            columns = result.keys()
            
            # Преобразуем в список словарей
            data = []
            for row in result:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Преобразуем datetime в строку
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[col] = value
                data.append(row_dict)
            
            # Сохраняем в JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Таблица {table_name}: {len(data)} записей -> {output_file}")
            return len(data)
            
    except Exception as e:
        logger.error(f"Ошибка при выгрузке таблицы {table_name}: {e}")
        return 0


def main():
    """Основная функция."""
    logger.info("Подключение к Supabase...")
    
    # Пробуем разные connection strings
    engine = None
    working_url = None
    
    for i, url in enumerate(CONNECTION_STRINGS, 1):
        logger.info(f"Попытка {i}/{len(CONNECTION_STRINGS)}: {url[:60]}...")
        try:
            test_engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
            with test_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                logger.info(f"Успешное подключение!")
                engine = test_engine
                working_url = url
                break
        except Exception as e:
            logger.warning(f"Не удалось подключиться: {str(e)[:100]}")
            continue
    
    if not engine:
        logger.error("Не удалось подключиться ни к одному из connection strings")
        logger.info("\nВозможные причины:")
        logger.info("1. Проект был удален или приостановлен в Supabase")
        logger.info("2. Неверный пароль")
        logger.info("3. Изменился project reference")
        logger.info("\nРешение:")
        logger.info("1. Откройте https://supabase.com/dashboard")
        logger.info("2. Проверьте статус проекта")
        logger.info("3. Получите новый connection string из Settings -> Database")
        sys.exit(1)
    
    try:
        
        # Проверяем подключение
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"Подключение успешно!")
            logger.info(f"PostgreSQL версия: {version[:50]}...")
            logger.info(f"Используется: {working_url[:60]}...")
        
        # Получаем список таблиц
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            logger.info(f"Найдено таблиц: {len(tables)}")
            for table in tables:
                logger.info(f"  - {table}")
        
        if not tables:
            logger.warning("Таблицы не найдены в базе данных")
            return
        
        # Создаем директорию для экспорта
        export_dir = Path("data/supabase_export")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Выгружаем каждую таблицу
        total_records = 0
        for table in tables:
            output_file = export_dir / f"{table}_{timestamp}.json"
            count = export_table_to_json(engine, table, output_file)
            total_records += count
        
        logger.info(f"\nЭкспорт завершен!")
        logger.info(f"Всего записей: {total_records}")
        logger.info(f"Файлы сохранены в: {export_dir}")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
