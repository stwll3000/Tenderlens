"""
Загрузка данных в Supabase используя прямой psycopg2 (обход проблемы с SQLAlchemy).
"""

import json
import psycopg2
import sys
import io
from pathlib import Path
from datetime import datetime

# Настройка вывода для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Параметры подключения (работающий вариант)
CONN_PARAMS = {
    "host": "aws-1-eu-north-1.pooler.supabase.com",
    "port": 5432,
    "database": "postgres",
    "user": "postgres.dnpjcxjjavzjmtfzlrip",
    "password": "1OSoLRpib7Tmd2Lu",
    "connect_timeout": 10
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

def insert_lots_batch(conn, lots, batch_size=100):
    """Вставка лотов пакетами."""
    cur = conn.cursor()
    
    # SQL для вставки
    insert_sql = """
        INSERT INTO lots (
            reg_number, url, name, price_start, price_contract,
            date_publish, date_end, customer_name, customer_inn,
            okpd2_code, okpd2_name, region_code
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (reg_number) DO UPDATE SET
            name = EXCLUDED.name,
            price_start = EXCLUDED.price_start,
            price_contract = EXCLUDED.price_contract,
            date_publish = EXCLUDED.date_publish,
            date_end = EXCLUDED.date_end,
            customer_name = EXCLUDED.customer_name,
            customer_inn = EXCLUDED.customer_inn,
            okpd2_code = EXCLUDED.okpd2_code,
            okpd2_name = EXCLUDED.okpd2_name,
            region_code = EXCLUDED.region_code
    """
    
    total = len(lots)
    inserted = 0
    updated = 0
    errors = 0
    
    for i in range(0, total, batch_size):
        batch = lots[i:i + batch_size]
        
        for lot in batch:
            try:
                # Подготовка данных
                values = (
                    lot.get('reg_number'),
                    lot.get('url'),
                    lot.get('name'),
                    lot.get('price_start'),
                    lot.get('price_contract'),
                    lot.get('date_publish'),
                    lot.get('date_end'),
                    lot.get('customer_name'),
                    lot.get('customer_inn'),
                    lot.get('okpd2_code'),
                    lot.get('okpd2_name'),
                    lot.get('region_code')
                )
                
                cur.execute(insert_sql, values)
                inserted += 1
                
            except Exception as e:
                errors += 1
                if errors <= 5:  # Показываем только первые 5 ошибок
                    print(f"  ✗ Ошибка при вставке {lot.get('reg_number')}: {str(e)[:100]}")
        
        # Коммитим каждый батч
        conn.commit()
        
        # Прогресс
        progress = min(i + batch_size, total)
        print(f"  Обработано: {progress}/{total} ({progress*100//total}%)")
    
    cur.close()
    return inserted, updated, errors

def main():
    print("=" * 70)
    print("ЗАГРУЗКА ДАННЫХ В SUPABASE (через psycopg2)")
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
    print("Подключение к Supabase...")
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
        print("Начинаем загрузку...")
        start_time = datetime.now()
        
        inserted, updated, errors = insert_lots_batch(conn, lots)
        
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
        print(f"Записей в БД после: {count_after}")
        print(f"Добавлено новых: {count_after - count_before}")
        print(f"Время выполнения: {duration:.2f} сек")
        print()
        
        if errors > 0:
            print(f"⚠ Обнаружено {errors} ошибок при загрузке")
        else:
            print("✓ Все данные успешно загружены!")
        
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"✗ Ошибка подключения: {e}")
        print()
        print("ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print("1. Проект Supabase находится в режиме 'Paused'")
        print("2. Неверные учетные данные")
        print("3. Проблемы с сетью")
        print()
        print("РЕШЕНИЕ:")
        print("1. Откройте https://supabase.com/dashboard")
        print("2. Найдите проект 'dnpjcxjjavzjmtfzlrip'")
        print("3. Если проект 'Paused' - нажмите 'Resume project'")
        print("4. Дождитесь активации (~2 минуты)")
        print("5. Запустите скрипт снова")
        
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
