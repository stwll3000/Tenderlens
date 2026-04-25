"""
Загрузка данных из JSON в PostgreSQL (Supabase).
Загружает все 6000 лотов из файла lots_multi_regions_6000_20260425.json
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from db.connection import SessionLocal
from db.models import Lot, Region, Customer
from sqlalchemy import text

def load_regions():
    """Загрузка регионов в БД"""
    
    regions_data = {
        "54": "Новосибирская область",
        "77": "Москва",
        "50": "Московская область",
        "78": "Санкт-Петербург",
        "47": "Ленинградская область",
        "66": "Свердловская область",
        "23": "Краснодарский край",
        "16": "Республика Татарстан",
        "74": "Челябинская область",
        "63": "Самарская область",
        "61": "Ростовская область",
        "59": "Пермский край",
    }
    
    db = SessionLocal()
    
    try:
        for code, name in regions_data.items():
            # Проверяем, существует ли регион
            existing = db.query(Region).filter(Region.code == code).first()
            
            if not existing:
                region = Region(code=code, name=name)
                db.add(region)
                print(f"✓ Добавлен регион: {name}")
        
        db.commit()
        print(f"\n[SUCCESS] Загружено {len(regions_data)} регионов")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Ошибка при загрузке регионов: {e}")
    finally:
        db.close()


def load_lots_from_json(json_file: str, batch_size: int = 100):
    """
    Загрузка лотов из JSON файла в БД
    
    Args:
        json_file: путь к JSON файлу
        batch_size: размер батча для загрузки
    """
    
    print(f"Загрузка данных из {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Найдено {len(data)} лотов")
    
    db = SessionLocal()
    
    try:
        # Очищаем таблицу lots (опционально)
        response = input("\nОчистить таблицу lots перед загрузкой? (yes/no): ")
        if response.lower() in ['yes', 'y', 'да']:
            db.execute(text("TRUNCATE TABLE lots CASCADE"))
            db.commit()
            print("✓ Таблица lots очищена")
        
        loaded = 0
        skipped = 0
        
        for i, lot_data in enumerate(data, 1):
            try:
                # Проверяем, существует ли лот
                existing = db.query(Lot).filter(
                    Lot.reg_number == lot_data.get('reg_number')
                ).first()
                
                if existing:
                    skipped += 1
                    continue
                
                # Создаём объект Lot
                lot = Lot(
                    reg_number=lot_data.get('reg_number'),
                    url=lot_data.get('url'),
                    law=lot_data.get('law'),
                    purchase_method=lot_data.get('purchase_method', ''),
                    status=lot_data.get('status', ''),
                    object_name=lot_data.get('object_name', ''),
                    customer_name=lot_data.get('customer_name', ''),
                    customer_url=lot_data.get('customer_url', ''),
                    initial_price=float(lot_data.get('initial_price', 0)),
                    region_code=lot_data.get('region_code'),
                    region_name=lot_data.get('region_name'),
                    scraped_at=datetime.fromisoformat(lot_data.get('scraped_at')),
                    
                    # Новые поля (если есть)
                    published_date=lot_data.get('published_date'),
                    updated_date=lot_data.get('updated_date'),
                    deadline_date=lot_data.get('deadline_date'),
                    okpd2_codes=json.dumps(lot_data.get('okpd2_codes', [])) if lot_data.get('okpd2_codes') else None,
                    participants_count=lot_data.get('participants_count'),
                )
                
                db.add(lot)
                loaded += 1
                
                # Коммитим батчами
                if loaded % batch_size == 0:
                    db.commit()
                    print(f"Загружено {loaded}/{len(data)} лотов...")
                
            except Exception as e:
                print(f"Ошибка при загрузке лота {lot_data.get('reg_number')}: {e}")
                continue
        
        # Финальный коммит
        db.commit()
        
        print(f"\n[SUCCESS] Загрузка завершена!")
        print(f"  Загружено: {loaded}")
        print(f"  Пропущено (дубликаты): {skipped}")
        print(f"  Всего в файле: {len(data)}")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Критическая ошибка: {e}")
    finally:
        db.close()


def main():
    """Главная функция"""
    
    print("="*60)
    print("ЗАГРУЗКА ДАННЫХ В POSTGRESQL")
    print("="*60)
    
    # Загружаем регионы
    print("\n1. Загрузка регионов...")
    load_regions()
    
    # Загружаем лоты
    print("\n2. Загрузка лотов...")
    json_file = "data/lots_multi_regions_6000_20260425.json"
    
    if not Path(json_file).exists():
        print(f"[ERROR] Файл {json_file} не найден!")
        return
    
    load_lots_from_json(json_file, batch_size=100)
    
    print("\n" + "="*60)
    print("ЗАГРУЗКА ЗАВЕРШЕНА")
    print("="*60)


if __name__ == "__main__":
    main()
