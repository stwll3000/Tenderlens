"""
Тест прямого подключения к Supabase (Direct Connection).
"""

import sys
import io
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

# Настройка вывода для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Прямое подключение к базе (без pooler)
direct_host = "db.dnpjcxjjavzjmtfzlrip.supabase.co"
password = "1OSoLRpib7Tmd2Lu"

configs = [
    {
        "name": "Direct Connection (port 5432)",
        "host": direct_host,
        "port": 5432,
    },
    {
        "name": "Direct Connection (port 6543)",
        "host": direct_host,
        "port": 6543,
    },
]

print("=" * 70)
print("ТЕСТИРОВАНИЕ ПРЯМОГО ПОДКЛЮЧЕНИЯ К SUPABASE")
print("=" * 70)
print()

for i, config in enumerate(configs, 1):
    print(f"{i}. {config['name']}")
    print(f"   Host: {config['host']}")
    print(f"   Port: {config['port']}")
    
    # Тест с psycopg2
    print("   [psycopg2]")
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database="postgres",
            user="postgres",
            password=password,
            connect_timeout=10
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print(f"     ✓ Version: {version.split(',')[0]}")
        
        cur.execute("SELECT COUNT(*) FROM customers")
        count = cur.fetchone()[0]
        print(f"     ✓ Customers: {count}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        error_msg = str(e).strip()
        print(f"     ✗ Ошибка: {error_msg[:100]}")
    
    # Тест с SQLAlchemy
    print("   [SQLAlchemy]")
    try:
        url = f"postgresql://postgres:{password}@{config['host']}:{config['port']}/postgres"
        engine = create_engine(url, poolclass=NullPool, pool_pre_ping=True)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"     ✓ Version: {version.split(',')[0]}")
            
            result = conn.execute(text("SELECT COUNT(*) FROM customers"))
            count = result.fetchone()[0]
            print(f"     ✓ Customers: {count}")
        
        engine.dispose()
        
    except Exception as e:
        error_msg = str(e)
        print(f"     ✗ Ошибка: {error_msg[:100]}")
    
    print()

print("=" * 70)
print()
print("ПРИМЕЧАНИЕ:")
print("Если прямое подключение не работает, это означает что:")
print("1. Проект Supabase находится в режиме 'Paused'")
print("2. Проект был удален или недоступен")
print("3. Нужно проверить статус в Dashboard: https://supabase.com/dashboard")
