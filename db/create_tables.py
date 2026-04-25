"""
Создание таблиц напрямую через SQL для обхода проблем с Supabase pooler.
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# SQL для создания таблиц
CREATE_TABLES_SQL = """
-- Таблица регионов
CREATE TABLE IF NOT EXISTS regions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(2) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_regions_code ON regions(code);

-- Таблица заказчиков
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    url VARCHAR(500) UNIQUE NOT NULL,
    inn VARCHAR(12),
    kpp VARCHAR(9),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customers_url ON customers(url);
CREATE INDEX IF NOT EXISTS idx_customers_inn ON customers(inn);

-- Таблица лотов
CREATE TABLE IF NOT EXISTS lots (
    id BIGSERIAL PRIMARY KEY,
    reg_number VARCHAR(50) UNIQUE NOT NULL,
    url VARCHAR(500) NOT NULL,
    law VARCHAR(10) NOT NULL,
    purchase_method VARCHAR(255) NOT NULL,
    status VARCHAR(100) NOT NULL,
    object_name TEXT NOT NULL,
    customer_name TEXT NOT NULL,
    customer_url VARCHAR(500) NOT NULL,
    initial_price FLOAT NOT NULL,
    final_price FLOAT,
    price_reduction_pct FLOAT,
    region_code VARCHAR(2) NOT NULL,
    region_name VARCHAR(255) NOT NULL,
    scraped_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lots_reg_number ON lots(reg_number);
CREATE INDEX IF NOT EXISTS idx_lots_law ON lots(law);
CREATE INDEX IF NOT EXISTS idx_lots_status ON lots(status);
CREATE INDEX IF NOT EXISTS idx_lots_customer_url ON lots(customer_url);
CREATE INDEX IF NOT EXISTS idx_lots_initial_price ON lots(initial_price);
CREATE INDEX IF NOT EXISTS idx_lots_region_code ON lots(region_code);
CREATE INDEX IF NOT EXISTS idx_lots_scraped_at ON lots(scraped_at);
CREATE INDEX IF NOT EXISTS idx_lots_region_law ON lots(region_code, law);
CREATE INDEX IF NOT EXISTS idx_lots_status_scraped ON lots(status, scraped_at);
CREATE INDEX IF NOT EXISTS idx_lots_customer_price ON lots(customer_url, initial_price);
"""

def create_tables():
    """Создание таблиц через прямой SQL."""
    print("Создание таблиц в PostgreSQL...")
    
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        cur.execute(CREATE_TABLES_SQL)
        print("[OK] Таблицы успешно созданы")
    except Exception as e:
        print(f"[ERROR] Ошибка при создании таблиц: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_tables()
