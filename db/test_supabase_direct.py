"""
Прямое подключение к Supabase через psycopg2.
"""

import psycopg2
import json
import sys
import io
from datetime import datetime
from pathlib import Path

# Настройка вывода для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connection parameters
conn_params = {
    "host": "aws-1-eu-north-1.pooler.supabase.com",
    "port": 6543,
    "database": "postgres",
    "user": "postgres.dnpjcxjjavzjmtfzlrip",
    "password": "1OSoLRpib7Tmd2Lu",
    "connect_timeout": 10
}

print("Попытка подключения к Supabase...")
print(f"Host: {conn_params['host']}")
print(f"Port: {conn_params['port']}")
print(f"User: {conn_params['user']}")
print()

try:
    # Подключаемся
    conn = psycopg2.connect(**conn_params)
    print("✓ Подключение успешно!")
    
    # Создаем курсор
    cur = conn.cursor()
    
    # Проверяем версию PostgreSQL
    cur.execute("SELECT version()")
    version = cur.fetchone()[0]
    print(f"PostgreSQL: {version[:80]}")
    print()
    
    # Получаем список таблиц
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    print(f"Найдено таблиц: {len(tables)}")
    if tables:
        for table in tables:
            # Получаем количество записей
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  - {table}: {count} записей")
    else:
        print("  (таблицы не найдены)")
    print()
    
    # Если есть таблицы, экспортируем их
    if tables:
        export_dir = Path("data/supabase_export")
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print("Начинаем экспорт данных...")
        total_records = 0
        
        for table in tables:
            # Получаем данные
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()
            
            # Получаем названия колонок
            columns = [desc[0] for desc in cur.description]
            
            # Преобразуем в список словарей
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    row_dict[col] = value
                data.append(row_dict)
            
            # Сохраняем в JSON
            output_file = export_dir / f"{table}_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"  ✓ {table}: {len(data)} записей -> {output_file.name}")
            total_records += len(data)
        
        print()
        print(f"Экспорт завершен!")
        print(f"Всего записей: {total_records}")
        print(f"Файлы сохранены в: {export_dir}")
    
    # Закрываем соединение
    cur.close()
    conn.close()
    
except psycopg2.OperationalError as e:
    print(f"✗ Ошибка подключения: {e}")
    print()
    print("Возможные причины:")
    print("1. Проект был удален или приостановлен в Supabase")
    print("2. Неверный пароль или project reference")
    print("3. Проблемы с сетью или firewall")
    print()
    print("Решение:")
    print("1. Откройте https://supabase.com/dashboard")
    print("2. Проверьте статус проекта")
    print("3. Получите актуальный connection string из Settings -> Database")
    sys.exit(1)
    
except Exception as e:
    print(f"✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
