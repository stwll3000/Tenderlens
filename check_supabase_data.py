"""
Проверка количества записей в Supabase.
"""

import os
import sys
import io
from dotenv import load_dotenv
from supabase import create_client, Client

# Настройка вывода для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Загрузка переменных окружения
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("=" * 70)
print("ПРОВЕРКА ДАННЫХ В SUPABASE")
print("=" * 70)
print()

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✓ Подключение успешно")
    print()
    
    # Проверяем количество записей в каждой таблице
    tables = ["regions", "customers", "lots"]
    
    for table in tables:
        try:
            response = supabase.table(table).select("*", count="exact").limit(1).execute()
            count = response.count if hasattr(response, 'count') else len(response.data)
            print(f"  {table}: {count} записей")
        except Exception as e:
            print(f"  {table}: ✗ Ошибка - {str(e)[:100]}")
    
    print()
    print("=" * 70)
    
    # Показываем последние 5 загруженных лотов
    print("\nПоследние 5 загруженных лотов:")
    print("-" * 70)
    try:
        response = supabase.table("lots").select("reg_number, object_name, initial_price, region_name").order("created_at", desc=True).limit(5).execute()
        
        for i, lot in enumerate(response.data, 1):
            print(f"{i}. {lot.get('reg_number')}")
            print(f"   {lot.get('object_name', '')[:60]}...")
            print(f"   Цена: {lot.get('initial_price')} руб.")
            print(f"   Регион: {lot.get('region_name')}")
            print()
    except Exception as e:
        print(f"✗ Ошибка: {e}")

except Exception as e:
    print(f"✗ Ошибка подключения: {e}")
    import traceback
    traceback.print_exc()
