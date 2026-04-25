"""
Загрузка оставшихся лотов с задержкой между запросами.
"""

import json
import psycopg2
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def load_remaining_lots():
    """Загрузка оставшихся лотов."""
    print("Загрузка оставшихся лотов...")
    
    # Читаем JSON
    with open("data/lots_all_20260425_173650.json", 'r', encoding='utf-8') as f:
        lots_data = json.load(f)
    
    print(f"Всего лотов в JSON: {len(lots_data)}")
    
    # Проверяем какие уже загружены
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT reg_number FROM lots")
    loaded_numbers = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()
    
    print(f"Уже загружено: {len(loaded_numbers)} лотов")
    
    # Фильтруем незагруженные
    remaining = [lot for lot in lots_data if lot['reg_number'] not in loaded_numbers]
    print(f"Осталось загрузить: {len(remaining)} лотов\n")
    
    if not remaining:
        print("[OK] Все лоты уже загружены!")
        return
    
    loaded = 0
    failed = 0
    
    for i, lot in enumerate(remaining):
        try:
            # Новое соединение для каждого лота
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = True
            cur = conn.cursor()
            
            scraped_at = lot['scraped_at']
            if isinstance(scraped_at, str):
                scraped_at = datetime.fromisoformat(scraped_at.replace('Z', '+00:00'))
            
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
            
            cur.close()
            conn.close()
            loaded += 1
            
            if (i + 1) % 10 == 0:
                print(f"  Загружено {i + 1}/{len(remaining)} лотов...")
            
            # Небольшая задержка чтобы не перегружать pooler
            time.sleep(0.1)
            
        except Exception as e:
            failed += 1
            if failed <= 5:  # Показываем только первые 5 ошибок
                print(f"[WARNING] Ошибка при загрузке {lot['reg_number']}: {e}")
    
    print(f"\n[OK] Загружено: {loaded} лотов")
    if failed > 0:
        print(f"[WARNING] Ошибок: {failed}")
    
    # Финальная статистика
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM lots")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    print(f"\nВсего лотов в БД: {total}")

if __name__ == "__main__":
    load_remaining_lots()
