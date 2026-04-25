"""
Загрузка данных из JSON в PostgreSQL через прямой psycopg2.
"""

import json
import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def load_data():
    """Загрузка данных из JSON."""
    print("\n" + "=" * 70)
    print("  ЗАГРУЗКА ДАННЫХ В POSTGRESQL")
    print("=" * 70 + "\n")
    
    try:
        # 1. Загрузка регионов
        print("[1/3] Загрузка регионов...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        regions = [
            ("54", "Новосибирская область"),
            ("77", "Москва"),
            ("50", "Московская область"),
        ]
        
        for code, name in regions:
            cur.execute(
                "INSERT INTO regions (code, name) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                (code, name)
            )
        
        cur.close()
        conn.close()
        print("[OK] Регионы загружены\n")
        
        # 2. Загрузка лотов из JSON
        print("[2/3] Загрузка лотов из JSON...")
        json_path = "data/lots_all_20260425_173650.json"
        
        with open(json_path, 'r', encoding='utf-8') as f:
            lots_data = json.load(f)
        
        print(f"Прочитано {len(lots_data)} лотов из JSON")
        
        # Собираем уникальных заказчиков
        customers = {}
        for lot in lots_data:
            url = lot['customer_url']
            if url not in customers:
                customers[url] = lot['customer_name']
        
        print(f"Найдено {len(customers)} уникальных заказчиков")
        
        # Загружаем заказчиков (по одному с переподключением)
        for i, (url, name) in enumerate(customers.items()):
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = True
            cur = conn.cursor()
            
            try:
                cur.execute(
                    "INSERT INTO customers (name, url) VALUES (%s, %s) ON CONFLICT (url) DO NOTHING",
                    (name, url)
                )
            except Exception as e:
                print(f"[WARNING] Ошибка при загрузке заказчика: {e}")
            finally:
                cur.close()
                conn.close()
            
            if (i + 1) % 10 == 0:
                print(f"  Загружено {i + 1}/{len(customers)} заказчиков...")
        
        print("[OK] Заказчики загружены")
        
        # Загружаем лоты
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        loaded = 0
        skipped = 0
        
        for lot in lots_data:
            # Преобразуем scraped_at в datetime
            scraped_at = lot['scraped_at']
            if isinstance(scraped_at, str):
                scraped_at = datetime.fromisoformat(scraped_at.replace('Z', '+00:00'))
            
            try:
                cur.execute("""
                    INSERT INTO lots (
                        reg_number, url, law, purchase_method, status,
                        object_name, customer_name, customer_url,
                        initial_price, region_code, region_name, scraped_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reg_number) DO NOTHING
                """, (
                    lot['reg_number'],
                    lot['url'],
                    lot['law'],
                    lot['purchase_method'],
                    lot['status'],
                    lot['object_name'],
                    lot['customer_name'],
                    lot['customer_url'],
                    lot['initial_price'],
                    lot['region_code'],
                    lot['region_name'],
                    scraped_at
                ))
                
                if cur.rowcount > 0:
                    loaded += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"[WARNING] Ошибка при загрузке лота {lot['reg_number']}: {e}")
                skipped += 1
        
        cur.close()
        conn.close()
        print(f"[OK] Загружено: {loaded} лотов")
        if skipped > 0:
            print(f"  Пропущено (дубликаты): {skipped} лотов\n")
        
        # 3. Статистика
        print("[3/3] Статистика БД:")
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM regions")
        regions_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM customers")
        customers_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM lots")
        lots_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        print(f"  Регионов:    {regions_count}")
        print(f"  Заказчиков:  {customers_count}")
        print(f"  Лотов:       {lots_count}")
        
        print("\n" + "=" * 70)
        print("  [SUCCESS] ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        raise

if __name__ == "__main__":
    load_data()
