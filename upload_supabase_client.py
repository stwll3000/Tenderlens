"""
Загрузка данных в Supabase используя официальный Python клиент.
"""

import json
import os
import sys
import io
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Настройка вывода для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Загрузка переменных окружения
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Путь к данным
DATA_FILE = Path("data/lots_multi_regions_6000_20260425.json")

def load_json_data(file_path):
    """Загрузка данных из JSON файла."""
    print(f"Загрузка данных из {file_path.name}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"✓ Загружено {len(data)} записей")
    return data

def transform_lot_for_db(lot):
    """Преобразование данных лота в формат БД."""
    return {
        "reg_number": lot.get("reg_number"),
        "url": lot.get("url"),
        "law": lot.get("law"),
        "purchase_method": lot.get("purchase_method"),
        "status": lot.get("status"),
        "object_name": lot.get("object_name"),
        "customer_name": lot.get("customer_name"),
        "customer_url": lot.get("customer_url"),
        "initial_price": lot.get("initial_price"),
        "final_price": lot.get("final_price"),
        "price_reduction_pct": lot.get("price_reduction_pct"),
        "region_code": lot.get("region_code"),
        "region_name": lot.get("region_name"),
        "published_date": lot.get("published_date"),
        "updated_date": lot.get("updated_date"),
        "deadline_date": lot.get("deadline_date"),
        "okpd2_codes": json.dumps(lot.get("okpd2_codes")) if lot.get("okpd2_codes") else None,
        "participants_count": lot.get("participants_count"),
        "scraped_at": lot.get("scraped_at"),
    }

def upload_lots_batch(supabase: Client, lots, batch_size=100):
    """Загрузка лотов пакетами."""
    total = len(lots)
    uploaded = 0
    errors = 0
    
    print(f"\nНачинаем загрузку {total} лотов пакетами по {batch_size}...")
    print()
    
    for i in range(0, total, batch_size):
        batch = lots[i:i + batch_size]
        
        # Преобразуем данные
        batch_data = [transform_lot_for_db(lot) for lot in batch]
        
        try:
            # Используем upsert для вставки/обновления
            response = supabase.table("lots").upsert(
                batch_data,
                on_conflict="reg_number"
            ).execute()
            
            uploaded += len(batch)
            progress = min(i + batch_size, total)
            print(f"  ✓ Обработано: {progress}/{total} ({progress*100//total}%)")
            
        except Exception as e:
            errors += len(batch)
            print(f"  ✗ Ошибка при загрузке батча {i//batch_size + 1}: {str(e)[:150]}")
    
    return uploaded, errors

def main():
    print("=" * 70)
    print("ЗАГРУЗКА ДАННЫХ В SUPABASE")
    print("=" * 70)
    print()
    
    # Проверка credentials
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("✗ Ошибка: SUPABASE_URL или SUPABASE_KEY не найдены в .env")
        return
    
    print(f"Supabase URL: {SUPABASE_URL}")
    print()
    
    # Проверка файла
    if not DATA_FILE.exists():
        print(f"✗ Файл не найден: {DATA_FILE}")
        return
    
    # Загрузка данных
    lots = load_json_data(DATA_FILE)
    print()
    
    # Подключение к Supabase
    print("Подключение к Supabase...")
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✓ Клиент создан")
        print()
        
        # Проверка текущего количества записей
        print("Проверка текущего состояния БД...")
        try:
            response = supabase.table("lots").select("reg_number", count="exact").limit(1).execute()
            count_before = response.count if hasattr(response, 'count') else 0
            print(f"Записей в БД до загрузки: {count_before}")
        except Exception as e:
            print(f"⚠ Не удалось получить количество записей: {e}")
            count_before = 0
        print()
        
        # Загрузка данных
        start_time = datetime.now()
        
        uploaded, errors = upload_lots_batch(supabase, lots, batch_size=100)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Проверка после загрузки
        print()
        print("Проверка результата...")
        try:
            response = supabase.table("lots").select("reg_number", count="exact").limit(1).execute()
            count_after = response.count if hasattr(response, 'count') else 0
            print(f"Записей в БД после загрузки: {count_after}")
        except Exception as e:
            print(f"⚠ Не удалось получить количество записей: {e}")
            count_after = count_before
        
        print()
        print("=" * 70)
        print("РЕЗУЛЬТАТ")
        print("=" * 70)
        print(f"Записей обработано: {len(lots)}")
        print(f"Успешно загружено: {uploaded}")
        print(f"Ошибок: {errors}")
        print(f"Записей в БД после: {count_after}")
        print(f"Добавлено новых: {count_after - count_before}")
        print(f"Время выполнения: {duration:.2f} сек")
        print()
        
        if errors > 0:
            print(f"⚠ Обнаружено {errors} ошибок при загрузке")
        else:
            print("✓ Все данные успешно загружены!")
        
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
