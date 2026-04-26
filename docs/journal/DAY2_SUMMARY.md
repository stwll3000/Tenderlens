# День 2 — Настройка базы данных (25.04.2026)

## ✅ Выполнено

### 1. SQLAlchemy модели (`db/models.py`)
Созданы три таблицы:
- **Region** — справочник регионов РФ (code, name)
- **Customer** — заказчики с полями для будущего расширения (ИНН, КПП)
- **Lot** — лоты/закупки со всеми полями из парсера

Особенности:
- Type hints для всех полей
- Индексы на часто используемые поля (reg_number, region_code, customer_url, initial_price)
- Составные индексы для аналитических запросов
- Поддержка дедупликации через UNIQUE constraints

### 2. Подключение к PostgreSQL (`db/connection.py`)
- Настроено подключение через SQLAlchemy
- Использован NullPool для совместимости с Supabase
- Реализованы функции:
  - `get_db()` — context manager для сессий
  - `init_db()` — создание таблиц
  - `test_connection()` — проверка подключения
- Автоматическая загрузка DATABASE_URL из `.env`

### 3. Alembic для миграций
Создана структура:
- `alembic/` — директория миграций
- `alembic.ini` — конфигурация
- `alembic/env.py` — настройка окружения с автоимпортом моделей
- `alembic/versions/` — папка для файлов миграций

### 4. Загрузчик данных (`db/loader.py`)
Функции:
- `load_regions()` — загрузка справочника регионов
- `extract_customers()` — извлечение уникальных заказчиков из лотов
- `load_lots_from_json()` — загрузка лотов из JSON с дедупликацией
- `get_stats()` — статистика по БД

Особенности:
- Использование PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`
- Автоматическая обработка дубликатов
- Подробное логирование процесса

### 5. Скрипт инициализации (`db/init_database.py`)
Автоматизированный процесс:
1. Проверка подключения к PostgreSQL
2. Создание таблиц
3. Загрузка справочника регионов
4. Загрузка лотов из JSON
5. Вывод финальной статистики

### 6. Документация
- `SETUP_DATABASE.md` — подробная инструкция по настройке Supabase
- Обновлен `.env.example` с инструкциями
- Обновлен `README.md` с новой структурой проекта

## 📊 Структура БД

### Таблица: regions
```sql
- id (PK, autoincrement)
- code (VARCHAR(2), UNIQUE, indexed)
- name (VARCHAR(255))
- created_at (TIMESTAMP)
```

### Таблица: customers
```sql
- id (PK, autoincrement)
- name (TEXT)
- url (VARCHAR(500), UNIQUE, indexed)
- inn (VARCHAR(12), nullable, indexed)
- kpp (VARCHAR(9), nullable)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
```

### Таблица: lots
```sql
- id (PK, BIGINT, autoincrement)
- reg_number (VARCHAR(50), UNIQUE, indexed)
- url (VARCHAR(500))
- law (VARCHAR(10), indexed)
- purchase_method (VARCHAR(255))
- status (VARCHAR(100), indexed)
- object_name (TEXT)
- customer_name (TEXT)
- customer_url (VARCHAR(500), indexed)
- initial_price (FLOAT, indexed)
- final_price (FLOAT, nullable)
- price_reduction_pct (FLOAT, nullable)
- region_code (VARCHAR(2), indexed)
- region_name (VARCHAR(255))
- scraped_at (TIMESTAMP, indexed)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)

Индексы:
- idx_region_law (region_code, law)
- idx_status_scraped (status, scraped_at)
- idx_customer_price (customer_url, initial_price)
```

## 🎯 Следующие шаги

### Для пользователя:
1. Создать проект в Supabase (https://supabase.com)
2. Получить DATABASE_URL из Settings > Database
3. Создать `.env` файл и добавить DATABASE_URL
4. Запустить: `python db/init_database.py`

### После загрузки данных:
1. Масштабировать парсер до 1000+ лотов
2. Начать аналитику в Jupyter notebooks
3. Реализовать первые метрики (снижение цены, конкурентность)

## 📝 Команды для работы

```bash
# Проверка подключения
python db/connection.py

# Инициализация БД и загрузка данных
python db/init_database.py

# Создание миграции (после изменения моделей)
alembic revision --autogenerate -m "Description"

# Применение миграций
alembic upgrade head

# Откат миграции
alembic downgrade -1
```

## 🔧 Технические детали

### Зависимости
- SQLAlchemy 2.0.23 — ORM
- Alembic 1.13.0 — миграции
- psycopg2-binary 2.9.9 — PostgreSQL драйвер
- python-dotenv 1.0.0 — работа с .env

### Особенности реализации
- Все функции с type hints
- Логирование через logging module
- Context managers для безопасной работы с БД
- Автоматический rollback при ошибках
- Поддержка дедупликации на уровне БД

## ⏱️ Время выполнения
**~2 часа** (создание моделей, настройка подключения, документация)

## 📈 Прогресс проекта
**Фаза 1 (Сбор и структурирование данных): 60%**
- ✅ Парсер данных
- ✅ Валидация данных
- ✅ Модели БД
- ✅ Подключение к PostgreSQL
- ⏳ Загрузка данных в БД (ожидает настройки Supabase)
- ⏳ Масштабирование сбора до 1000+ лотов
