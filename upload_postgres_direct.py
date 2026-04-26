"""
Загрузка данных в Supabase через PostgreSQL (работающий метод).
"""

import json
import psycopg2
import sys
import io
from pathlib import Path
from datetime import datetime

# Настройка вывода для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Параметры подключения (проверенный рабочий вариант)
CONN_PARAMS = {
    "host": "aws-1-eu-north-1.pooler.supabase.com",
    "port": 5432,
    "database": "postgres",
    "user": "postgres.dnpjcxjjavzjmtfzlrip",
    "password": "1OSoLRpib7Tmd2Lu",
    "connect_timeout": 30
}

# Путь к данным
DATA_FILE = Path("data/lots_multi_regions_6000_20260425.json")

def load_json_data(file_path):
    """Загрузка данных из JSON файла."""
    print(f"Загрузка данных из {file_path.name}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"✓ Загружено {len(data)} записей")
    return data

def insert_lots_batch(conn, lots, batch_size=50):
    """Вставка лотов пакетами с правильными полями."""
    cur = conn.cursor()
    
    # SQL для вставки с правильными полями из models.py
    insert_sql = """
        INSERT INTO lots (
            reg_number, url, law, purchase_method, status, object_name,
            customer_name, customer_url, initial_price, final_price,
            price_reduction_pct, region_code, region_name,
            published_date, updated_date, deadline_date,
            okpd2_codes, participants_count, scraped_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (reg_number) DO UPDATE SET
            status = EXCLUDED.status,
            initial_price = EXCLUDED.initial_price,
            final_price = EXCLUDED.final_price,
            updated_date = EXCLUDED.updated_date
    """
    
    total = len(lots)
    inserted = 0
    errors = 0
    
    for i in range(0, total, batch_size):
        batch = lots[i:i + batch_size]
        
        for lot in batch:
            try:
                # Подготовка данных с правильными полями
                values = (
                    lot.get('reg_number'),
                    lot.get('url'),
                    lot.get('law', '44-ФЗ'),
                    lot.get('purchase_method', ''),
                    lot.get('status', ''),
                    lot.get('object_name', ''),
                    lot.get('customer_name', ''),
                    lot.get('customer_url', ''),
                    lot.get('initial_price', 0.0),
                    lot.get('final_price'),
                    lot.get('price_reduction_pct'),
                    lot.get('region_code', ''),
                    lot.get('region_name', ''),
                    lot.get('published_date'),
                    lot.get('updated_date'),
                    lot.get('deadline_date'),
                    json.dumps(lot.get('okpd2_codes')) if lot.get('okpd2_codes') else None,
                    lot.get('participants_count'),
                    lot.get('scraped_at', datetime.now().isoformat())
                )
                
                cur.execute(insert_sql, values)
                inserted += 1
                
            except Exception as e:
                errors += 1
                if errors <= 3:  # Показываем только первые 3 ошибки
                    print(f"  ✗ Ошибка: {lot.get('reg_number')}: {str(e)[:100]}")
        
        # Коммитим каждый батч
        try:
            conn.commit()
            progress = min(i + batch_size, total)
            print(f"  ✓ Обработано: {progress}/{total} ({progress*100//total}%)")
        except Exception as e:
            conn.rollback()
            print(f"  ✗ Ошибка коммита батча: {str(e)[:100]}")
            break
    
    cur.close()
    return inserted, errors

def main():
    print("=" * 70)
    print("ЗАГРУЗКА ДАННЫХ В SUPABASE (PostgreSQL)")
    print("=" * 70)
    print()
    
    # Проверка файла
    if not DATA_FILE.exists():
        print(f"✗ Файл не найден: {DATA_FILE}")
        return
    
    # Загрузка данных
    lots = load_json_data(DATA_FILE)
    print()
    
    # Подключение к БД
    print("Подключение к Supabase PostgreSQL...")
    print(f"Host: {CONN_PARAMS['host']}")
    print(f"Port: {CONN_PARAMS['port']}")
    
    try:
        conn = psycopg2.connect(**CONN_PARAMS)
        print("✓ Подключение успешно")
        print()
        
        # Проверка таблицы
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM lots")
        count_before = cur.fetchone()[0]
        print(f"Записей в БД до загрузки: {count_before}")
        cur.close()
        print()
        
        # Загрузка данных
        print("Начинаем загрузку (батчами по 50)...")
        start_time = datetime.now()
        
        inserted, errors = insert_lots_batch(conn, lots, batch_size=50)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Проверка после загрузки
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM lots")
        count_after = cur.fetchone()[0]
        cur.close()
        
        print()
        print("=" * 70)
        print("РЕЗУЛЬТАТ")
        print("=" * 70)
        print(f"Записей обработано: {len(lots)}")
        print(f"Успешно вставлено: {inserted}")
        print(f"Ошибок: {errors}")
        print(f"Записей в БД до: {count_before}")
        print(f"Записей в БД после: {count_after}")
        print(f"Добавлено новых: {count_after - count_before}")
        print(f"Время выполнения: {duration:.2f} сек")
        print()
        
        if errors > 0:
            print(f"⚠ Обнаружено {errors} ошибок при загрузке")
        else:
            print("✓ Все данные успешно загружены!")
        
        conn.close()
        
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
