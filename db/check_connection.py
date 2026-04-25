"""
Проверка подключения к Supabase PostgreSQL.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from db.connection import engine
from sqlalchemy import text

def check_connection():
    """Проверка подключения к БД"""
    
    print("Проверка подключения к Supabase PostgreSQL...\n")
    
    try:
        with engine.connect() as conn:
            # Проверка версии PostgreSQL
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✓ Подключение успешно!")
            print(f"PostgreSQL версия: {version[:50]}...\n")
            
            # Проверка существующих таблиц
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            print(f"Таблицы в БД ({len(tables)}):")
            for table in tables:
                print(f"  - {table}")
            
            # Проверка количества записей
            if 'lots' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM lots"))
                count = result.scalar()
                print(f"\nЗаписей в таблице lots: {count}")
            
            if 'regions' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM regions"))
                count = result.scalar()
                print(f"Записей в таблице regions: {count}")
            
            if 'customers' in tables:
                result = conn.execute(text("SELECT COUNT(*) FROM customers"))
                count = result.scalar()
                print(f"Записей в таблице customers: {count}")
            
            print("\n[SUCCESS] База данных готова к работе!")
            return True
            
    except Exception as e:
        print(f"[ERROR] Ошибка подключения: {e}")
        return False

if __name__ == "__main__":
    check_connection()
