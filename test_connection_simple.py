"""
Простой тест подключения к Supabase.
"""

import psycopg2
import sys
import io

# Настройка вывода для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Варианты подключения для тестирования
connections = [
    {
        "name": "Transaction Pooler (aws-0, port 6543)",
        "host": "aws-0-eu-north-1.pooler.supabase.com",
        "port": 6543,
    },
    {
        "name": "Session Pooler (aws-0, port 5432)",
        "host": "aws-0-eu-north-1.pooler.supabase.com",
        "port": 5432,
    },
    {
        "name": "Transaction Pooler (aws-1, port 6543)",
        "host": "aws-1-eu-north-1.pooler.supabase.com",
        "port": 6543,
    },
    {
        "name": "Session Pooler (aws-1, port 5432)",
        "host": "aws-1-eu-north-1.pooler.supabase.com",
        "port": 5432,
    },
]

# Общие параметры
database = "postgres"
user = "postgres.dnpjcxjjavzjmtfzlrip"
password = "1OSoLRpib7Tmd2Lu"

print("=" * 70)
print("ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ К SUPABASE")
print("=" * 70)
print()

success_count = 0

for i, conn_config in enumerate(connections, 1):
    print(f"{i}. {conn_config['name']}")
    print(f"   Host: {conn_config['host']}")
    print(f"   Port: {conn_config['port']}")
    
    try:
        conn = psycopg2.connect(
            host=conn_config['host'],
            port=conn_config['port'],
            database=database,
            user=user,
            password=password,
            connect_timeout=10
        )
        
        print("   Статус: ✓ ПОДКЛЮЧЕНИЕ УСПЕШНО")
        
        # Пробуем выполнить простой запрос
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print(f"   PostgreSQL: {version.split(',')[0]}")
        
        # Пробуем получить список таблиц
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"   Таблицы: {', '.join(tables) if tables else 'нет таблиц'}")
        
        cur.close()
        conn.close()
        success_count += 1
        
    except psycopg2.OperationalError as e:
        error_msg = str(e).strip()
        if "tenant/user" in error_msg and "not found" in error_msg:
            print("   Статус: ✗ ПРОЕКТ НЕ НАЙДЕН")
            print("   Ошибка: Проект был удален или не существует")
        elif "server closed the connection" in error_msg:
            print("   Статус: ✗ СОЕДИНЕНИЕ ЗАКРЫТО СЕРВЕРОМ")
            print("   Ошибка: Проект приостановлен или недоступен")
        else:
            print(f"   Статус: ✗ ОШИБКА ПОДКЛЮЧЕНИЯ")
            print(f"   Ошибка: {error_msg[:100]}")
    
    except Exception as e:
        print(f"   Статус: ✗ НЕИЗВЕСТНАЯ ОШИБКА")
        print(f"   Ошибка: {str(e)[:100]}")
    
    print()

print("=" * 70)
print(f"РЕЗУЛЬТАТ: {success_count}/{len(connections)} подключений успешно")
print("=" * 70)
print()

if success_count == 0:
    print("❌ НИ ОДНО ПОДКЛЮЧЕНИЕ НЕ УДАЛОСЬ")
    print()
    print("ДИАГНОЗ:")
    print("Проект Supabase 'postgres.dnpjcxjjavzjmtfzlrip' не существует или был удален.")
    print()
    print("РЕШЕНИЕ:")
    print("1. Откройте https://supabase.com/dashboard")
    print("2. Проверьте список ваших проектов")
    print("3. Если проект существует:")
    print("   - Проверьте его статус (Active/Paused)")
    print("   - Скопируйте новый Connection String из Settings -> Database")
    print("   - Обновите DATABASE_URL в .env файле")
    print("4. Если проект был удален:")
    print("   - Создайте новый проект в Supabase")
    print("   - Скопируйте Connection String")
    print("   - Обновите DATABASE_URL в .env файле")
    print("   - Запустите: alembic upgrade head")
    print("   - Загрузите данные: python db/load_multi_regions.py")
else:
    print(f"✓ Успешно подключено через: {success_count} вариант(ов)")
    print()
    print("Теперь можно загружать данные в базу.")
