"""
Скрипт для подключения к Supabase и выгрузки данных.
"""

import json
import logging
import sys
import io
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Настройка логирования для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Transaction pooler connection string
DATABASE_URL = "postgresql://postgres.dnpjcxjjavzjmtfzlrip:1OSoLRpib7Tmd2Lu@aws-1-eu-north-1.pooler.supabase.com:6543/postgres"


def export_table_to_json(engine, table_name: str, output_file: Path):
    """Выгружает таблицу из PostgreSQL в JSON."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            columns = result.keys()
            
            data = []
            for row in result:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[col] = value
                data.append(row_dict)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Таблица {table_name}: {len(data)} записей -> {output_file.name}")
            return len(data)
            
    except Exception as e:
        logger.error(f"Ошибка при выгрузке таблицы {table_name}: {e}")
        return 0


def main():
    """Основная функция."""
    logger.info("Подключение к Supabase (transaction pooler)...")
    logger.info(f"Host: aws-1-eu-north-1.pooler.supabase.com:6543")
    
    try:
        # Создаем engine с увеличенным таймаутом
        engine = create_engine(
            DATABASE_URL, 
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 30,
                "options": "-c statement_timeout=30000"
            }
        )
        
        # Проверяем подключение
        logger.info("Проверка подключения...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"Успешно подключено!")
            logger.info(f"PostgreSQL: {version[:80]}")
        
        # Получаем список таблиц
        logger.info("\nПолучение списка таблиц...")
        inspector = inspect(engine)
        tables = inspector.get_table_names(schema='public')
        
        if not tables:
            logger.warning("Таблицы не найдены в схеме public")
            
            # Проверяем другие схемы
            schemas = inspector.get_schema_names()
            logger.info(f"Доступные схемы: {schemas}")
            
            for schema in schemas:
                if schema not in ['pg_catalog', 'information_schema']:
                    schema_tables = inspector.get_table_names(schema=schema)
                    if schema_tables:
                        logger.info(f"Таблицы в схеме {schema}: {schema_tables}")
            return
        
        logger.info(f"Найдено таблиц: {len(tables)}")
        for table in tables:
            logger.info(f"  - {table}")
        
        # Создаем директорию для экспорта
        export_dir = Path("data/supabase_export")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Выгружаем каждую таблицу
        logger.info(f"\nНачинаем экспорт в {export_dir}...")
        total_records = 0
        
        for table in tables:
            output_file = export_dir / f"{table}_{timestamp}.json"
            count = export_table_to_json(engine, table, output_file)
            total_records += count
        
        logger.info(f"\nЭкспорт завершен!")
        logger.info(f"Всего записей: {total_records}")
        logger.info(f"Файлы сохранены в: {export_dir}")
        
        # Создаем сводный файл
        summary = {
            "export_date": timestamp,
            "database": "Supabase PostgreSQL",
            "connection": "transaction pooler (port 6543)",
            "tables": tables,
            "total_records": total_records,
            "files": [f"{table}_{timestamp}.json" for table in tables]
        }
        
        summary_file = export_dir / f"_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сводка сохранена: {summary_file.name}")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
