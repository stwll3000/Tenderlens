"""
Загрузка данных из JSON в PostgreSQL.

Функции:
- load_regions: загрузка справочника регионов
- load_lots_from_json: загрузка лотов из JSON файла
- extract_customers: извлечение уникальных заказчиков из лотов
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from db.models import Region, Customer, Lot
from db.connection import SessionLocal

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_regions(db: Session) -> None:
    """
    Загрузка справочника регионов РФ.
    
    Args:
        db: SQLAlchemy сессия
    """
    regions_data = [
        {"code": "54", "name": "Новосибирская область"},
        {"code": "77", "name": "Москва"},
        {"code": "50", "name": "Московская область"},
        # Можно расширить полным списком регионов
    ]
    
    logger.info(f"Загрузка {len(regions_data)} регионов...")
    
    for region_dict in regions_data:
        # Используем INSERT ... ON CONFLICT DO NOTHING для PostgreSQL
        stmt = insert(Region).values(**region_dict)
        stmt = stmt.on_conflict_do_nothing(index_elements=['code'])
        db.execute(stmt)
    
    db.commit()
    logger.info("✓ Регионы загружены")


def extract_customers(lots_data: List[Dict[str, Any]], db: Session) -> None:
    """
    Извлечение и загрузка уникальных заказчиков из данных лотов.
    
    Args:
        lots_data: список словарей с данными лотов
        db: SQLAlchemy сессия
    """
    # Собираем уникальных заказчиков по URL
    customers_dict = {}
    for lot in lots_data:
        customer_url = lot.get("customer_url")
        if customer_url and customer_url not in customers_dict:
            customers_dict[customer_url] = {
                "name": lot.get("customer_name"),
                "url": customer_url,
            }
    
    logger.info(f"Найдено {len(customers_dict)} уникальных заказчиков")
    
    # Загружаем заказчиков
    for customer_data in customers_dict.values():
        stmt = insert(Customer).values(**customer_data)
        stmt = stmt.on_conflict_do_nothing(index_elements=['url'])
        db.execute(stmt)
    
    db.commit()
    logger.info("✓ Заказчики загружены")


def load_lots_from_json(json_path: str, db: Session) -> int:
    """
    Загрузка лотов из JSON файла в БД.
    
    Args:
        json_path: путь к JSON файлу
        db: SQLAlchemy сессия
    
    Returns:
        int: количество загруженных лотов
    """
    json_file = Path(json_path)
    
    if not json_file.exists():
        raise FileNotFoundError(f"Файл не найден: {json_path}")
    
    logger.info(f"Загрузка данных из {json_file.name}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        lots_data = json.load(f)
    
    logger.info(f"Прочитано {len(lots_data)} лотов из JSON")
    
    # Загружаем заказчиков
    extract_customers(lots_data, db)
    
    # Загружаем лоты
    loaded_count = 0
    skipped_count = 0
    
    for lot_dict in lots_data:
        # Преобразуем scraped_at в datetime
        if isinstance(lot_dict.get('scraped_at'), str):
            lot_dict['scraped_at'] = datetime.fromisoformat(
                lot_dict['scraped_at'].replace('Z', '+00:00')
            )
        
        # Используем INSERT ... ON CONFLICT DO NOTHING
        stmt = insert(Lot).values(**lot_dict)
        stmt = stmt.on_conflict_do_nothing(index_elements=['reg_number'])
        
        result = db.execute(stmt)
        
        if result.rowcount > 0:
            loaded_count += 1
        else:
            skipped_count += 1
    
    db.commit()
    
    logger.info(f"✓ Загружено: {loaded_count} лотов")
    if skipped_count > 0:
        logger.info(f"  Пропущено (дубликаты): {skipped_count} лотов")
    
    return loaded_count


def get_stats(db: Session) -> Dict[str, int]:
    """
    Получение статистики по БД.
    
    Args:
        db: SQLAlchemy сессия
    
    Returns:
        dict: статистика по таблицам
    """
    stats = {
        "regions": db.query(Region).count(),
        "customers": db.query(Customer).count(),
        "lots": db.query(Lot).count(),
    }
    return stats


def main():
    """Основная функция для загрузки данных."""
    logger.info("=" * 60)
    logger.info("ЗАГРУЗКА ДАННЫХ В POSTGRESQL")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 1. Загружаем регионы
        logger.info("\n[1/3] Загрузка регионов...")
        load_regions(db)
        
        # 2. Загружаем лоты из JSON
        logger.info("\n[2/3] Загрузка лотов...")
        json_path = "data/lots_all_20260425_173650.json"
        loaded = load_lots_from_json(json_path, db)
        
        # 3. Выводим статистику
        logger.info("\n[3/3] Статистика БД:")
        stats = get_stats(db)
        for table, count in stats.items():
            logger.info(f"  {table}: {count} записей")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Ошибка при загрузке: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
