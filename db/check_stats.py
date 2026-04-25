"""Проверка статистики БД."""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

print("=== СТАТИСТИКА БД ===\n")

# Регионы
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM regions')
print(f"Регионов: {cur.fetchone()[0]}")
cur.close()
conn.close()

# Заказчики
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM customers')
print(f"Заказчиков: {cur.fetchone()[0]}")
cur.close()
conn.close()

# Лоты
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM lots')
print(f"Лотов: {cur.fetchone()[0]}")
cur.close()
conn.close()

# По законам
print("\nПо законам:")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute('SELECT law, COUNT(*) FROM lots GROUP BY law')
for law, count in cur.fetchall():
    print(f"  {law}: {count}")
cur.close()
conn.close()

# По регионам
print("\nПо регионам:")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute('SELECT region_name, COUNT(*) FROM lots GROUP BY region_name')
for region, count in cur.fetchall():
    print(f"  {region}: {count}")
cur.close()
conn.close()

print("\n[SUCCESS] База данных успешно настроена!")
