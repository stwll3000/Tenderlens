"""
Тест подключения SQLAlchemy к Supabase.
"""

import sys
import io
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# Настройка вывода для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Тестируем разные варианты
configs = [
    {
        "name": "Session Pooler (5432) - NullPool",
        "url": "postgresql://postgres.dnpjcxjjavzjmtfzlrip:1OSoLRpib7Tmd2Lu@aws-1-eu-north-1.pooler.supabase.com:5432/postgres",
        "poolclass": NullPool,
        "pool_pre_ping": True,
    },
    {
        "name": "Session Pooler (5432) - QueuePool",
        "url": "postgresql://postgres.dnpjcxjjavzjmtfzlrip:1OSoLRpib7Tmd2Lu@aws-1-eu-north-1.pooler.supabase.com:5432/postgres",
        "poolclass": None,
        "pool_pre_ping": True,
    },
    {
        "name": "Transaction Pooler (6543) - NullPool",
        "url": "postgresql://postgres.dnpjcxjjavzjmtfzlrip:1OSoLRpib7Tmd2Lu@aws-1-eu-north-1.pooler.supabase.com:6543/postgres",
        "poolclass": NullPool,
        "pool_pre_ping": True,
    },
]

print("=" * 70)
print("ТЕСТИРОВАНИЕ SQLALCHEMY С SUPABASE")
print("=" * 70)
print()

for i, config in enumerate(configs, 1):
    print(f"{i}. {config['name']}")
    
    try:
        # Создаем engine
        engine_args = {
            "echo": False,
            "pool_pre_ping": config["pool_pre_ping"],
        }
        
        if config["poolclass"]:
            engine_args["poolclass"] = config["poolclass"]
        
        engine = create_engine(config["url"], **engine_args)
        
        # Пробуем подключиться
        with engine.connect() as conn:
            # Простой запрос
            result = conn.execute(text("SELECT 1 as test"))
            test_val = result.fetchone()[0]
            print(f"   ✓ SELECT 1: {test_val}")
            
            # Версия PostgreSQL
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"   ✓ Version: {version.split(',')[0]}")
            
            # Список таблиц
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"   ✓ Tables: {', '.join(tables)}")
            
            # Количество записей в первой таблице
            if tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {tables[0]}"))
                count = result.fetchone()[0]
                print(f"   ✓ {tables[0]} count: {count}")
            
            print(f"   Статус: ✓ ВСЕ ЗАПРОСЫ УСПЕШНЫ")
        
        engine.dispose()
        
    except Exception as e:
        error_msg = str(e)
        if "server closed the connection" in error_msg:
            print(f"   Статус: ✗ СЕРВЕР ЗАКРЫЛ СОЕДИНЕНИЕ")
        else:
            print(f"   Статус: ✗ ОШИБКА")
        print(f"   Ошибка: {error_msg[:150]}")
    
    print()

print("=" * 70)
