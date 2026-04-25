# Настройка Supabase для TenderLens

## Проблема с подключением

Текущий connection string не работает:
```
FATAL: (ENOTFOUND) tenant/user postgres.dnpjcxjjavzjmtfzlrip not found
```

Это означает, что проект был удален или изменен в Supabase.

## Решение

### Вариант 1: Получить новый connection string (рекомендуется)

1. Откройте [Supabase Dashboard](https://supabase.com/dashboard)
2. Выберите ваш проект или создайте новый
3. Перейдите в **Settings → Database**
4. Скопируйте **Connection string** в одном из режимов:
   - **Transaction mode** (порт 6543) — для коротких запросов
   - **Session mode** (порт 5432) — для длинных сессий
   - **Direct connection** — прямое подключение без pooler

5. Замените `[YOUR-PASSWORD]` на ваш пароль базы данных

6. Обновите `.env` файл:
```env
DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

### Вариант 2: Создать новый проект в Supabase

1. Откройте https://supabase.com/dashboard
2. Нажмите **New Project**
3. Укажите:
   - **Name**: TenderLens
   - **Database Password**: создайте надежный пароль (сохраните его!)
   - **Region**: выберите ближайший регион (например, Europe North)
4. Дождитесь создания проекта (~2 минуты)
5. Скопируйте connection string из **Settings → Database**

### Вариант 3: Работать с JSON (текущий режим)

Если Supabase не нужен срочно, продолжайте работать с JSON-файлами:
- Данные хранятся в `data/lots_*.json`
- Dashboard работает с JSON
- Telegram-бот работает с JSON
- PostgreSQL можно настроить позже

## Создание таблиц в Supabase

После получения нового connection string:

1. Обновите `.env` с новым DATABASE_URL

2. Создайте таблицы через Alembic:
```bash
# Создать миграцию
alembic revision --autogenerate -m "Initial schema"

# Применить миграцию
alembic upgrade head
```

3. Или создайте таблицы вручную через SQL Editor в Supabase:

```sql
-- Таблица регионов
CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(2) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_regions_code ON regions(code);

-- Таблица заказчиков
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    url VARCHAR(500) UNIQUE NOT NULL,
    inn VARCHAR(12),
    kpp VARCHAR(9),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_customers_url ON customers(url);
CREATE INDEX idx_customers_inn ON customers(inn);

-- Таблица лотов
CREATE TABLE lots (
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
    published_date VARCHAR(20),
    updated_date VARCHAR(20),
    deadline_date VARCHAR(20),
    okpd2_codes TEXT,
    participants_count INTEGER,
    scraped_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_lots_reg_number ON lots(reg_number);
CREATE INDEX idx_lots_law ON lots(law);
CREATE INDEX idx_lots_status ON lots(status);
CREATE INDEX idx_lots_initial_price ON lots(initial_price);
CREATE INDEX idx_lots_region_code ON lots(region_code);
CREATE INDEX idx_lots_customer_url ON lots(customer_url);
CREATE INDEX idx_lots_published_date ON lots(published_date);
CREATE INDEX idx_lots_deadline_date ON lots(deadline_date);
CREATE INDEX idx_lots_scraped_at ON lots(scraped_at);
CREATE INDEX idx_lots_region_law ON lots(region_code, law);
CREATE INDEX idx_lots_status_scraped ON lots(status, scraped_at);
CREATE INDEX idx_lots_customer_price ON lots(customer_url, initial_price);
```

## Загрузка данных в Supabase

После создания таблиц загрузите данные:

```bash
# Загрузить 6000 лотов из JSON в PostgreSQL
python db/load_multi_regions.py
```

## Проверка подключения

```bash
# Проверить подключение
python db/check_connection.py

# Проверить статистику в БД
python db/check_stats.py
```

## Troubleshooting

### Ошибка: "tenant/user not found"
- Проект был удален или изменен
- Получите новый connection string из Dashboard

### Ошибка: "password authentication failed"
- Неверный пароль в connection string
- Проверьте пароль в Supabase Dashboard → Settings → Database

### Ошибка: "connection timeout"
- Проверьте интернет-соединение
- Попробуйте другой режим pooler (transaction/session/direct)
- Проверьте firewall

### Ошибка: "SSL required"
- Добавьте `?sslmode=require` в конец connection string:
```
DATABASE_URL=postgresql://...postgres?sslmode=require
```

## Рекомендации

1. **Для разработки**: используйте JSON-файлы (быстрее, проще)
2. **Для продакшена**: используйте PostgreSQL (масштабируемость, SQL-запросы)
3. **Для бота**: JSON достаточно для начала
4. **Для аналитики**: PostgreSQL лучше для сложных запросов

## Полезные ссылки

- [Supabase Dashboard](https://supabase.com/dashboard)
- [Supabase Database Settings](https://supabase.com/dashboard/project/_/settings/database)
- [Supabase Documentation](https://supabase.com/docs)
