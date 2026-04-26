# CLAUDE.md — Контекст проекта TenderLens для AI-агентов

## Проект

**TenderLens** — аналитическая платформа рынка госзакупок РФ.
Цель: поиск прибыльных лотов для МСБ-поставщиков через скоринг (Profit Score).
Стек: Python 3.11+ · PostgreSQL (Supabase) · Streamlit · pandas · SQLAlchemy · Alembic.

## Быстрый старт

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка БД (нужен .env с DATABASE_URL)
cp .env.example .env
# Отредактируйте .env — добавьте Supabase DATABASE_URL

# Инициализация БД и загрузка данных
python db/init_database.py

# Запуск дашборда
streamlit run dashboard/app.py

# Запуск анализа (без БД, на синтетических данных)
python analysis/run_audit_analysis.py
```

## Структура проекта

```
tenderlens/
├── analytics/           # Аналитические модули (pandas-based, без БД)
│   ├── pricing.py       # Распределение НМЦ, перцентили, IQR-выбросы, α
│   ├── competition.py   # HHI, топ-заказчики, разрезы по региону/закону
│   └── temporal.py      # Дедлайны, сезонность, дни недели
│
├── scraper/             # Парсинг zakupki.gov.ru
│   ├── fetch_lots.py            # Базовый парсер (карточки лотов)
│   ├── fetch_lots_enhanced.py   # Расширенный парсер (+ детальные страницы)
│   ├── enrich_existing_lots.py  # Обогащение существующих лотов
│   ├── regions.py               # Справочник регионов (15 основных + 5 доп.)
│   ├── collect_*.py             # Скрипты массового сбора
│   └── validate_data.py         # Валидация собранных данных
│
├── db/                  # База данных
│   ├── models.py        # SQLAlchemy модели (Region, Customer, Lot)
│   ├── connection.py    # Engine + SessionLocal (Supabase PostgreSQL)
│   ├── loader.py        # Загрузка JSON → PostgreSQL (через SQLAlchemy)
│   ├── init_database.py # Создание таблиц + загрузка начальных данных
│   ├── create_tables.py # SQL-создание таблиц (обход pooler проблем)
│   └── load_*.py        # Разные скрипты загрузки данных
│
├── dashboard/           # Streamlit-дашборд
│   └── app.py           # Главное приложение (5 вкладок: цены, конкуренция,
│                        #   временной анализ, распределения, данные)
│
├── analysis/            # Аудит-анализ (offline, без БД)
│   ├── audit_analysis.py      # Генерация синтетических данных
│   └── run_audit_analysis.py  # 9 визуализаций по аудиту
│
├── alembic/             # Миграции БД
│   └── versions/        # Файлы миграций
│
├── data/                # Данные (gitignored: *.json, *.csv)
├── notebooks/           # Jupyter notebooks
├── scripts/             # Утилитарные скрипты анализа
└── docs/                # Документация (DAY*.md, планы, промпты)
```

## Схема БД (db/models.py)

```
regions:     id, code(2), name, created_at
customers:   id, name, url(unique, index), inn(nullable), kpp(nullable)
lots:        id, reg_number(unique), url, law, purchase_method, status,
             object_name, customer_name, customer_url, initial_price(float),
             final_price(nullable), price_reduction_pct(nullable),
             region_code(2), region_name, published_date(str DD.MM.YYYY),
             updated_date(str), deadline_date(str), okpd2_codes(JSON text),
             participants_count(nullable int), scraped_at
```

Составные индексы: `idx_region_law`, `idx_status_scraped`, `idx_customer_price`.

## Ключевые зависимости

- `db/connection.py` — требует `.env` с `DATABASE_URL` (PostgreSQL).
  Без `.env` импорт `db.connection` падает с `ValueError`.
- `dashboard/app.py` — ищет JSON в `data/` (приоритет: multi_regions > fast > all > enriched).
  Без JSON — показывает ошибку в Streamlit.
- `analytics/` — чистый pandas, без привязки к БД. Работают с любым DataFrame.
- `scraper/` — HTTP к zakupki.gov.ru с retry через tenacity. Требует сеть.

## Известные проблемы (из аудита)

1. **`final_price` заполнена у ~8.7%** лотов — нет парсера протоколов итогов
2. **HHI считается по заказчикам** (`competition.py:93-133`) — нужен HHI по поставщикам
3. **Нет таблиц `suppliers`, `lot_participations`** — блокирует Profit Score
4. **ОКПД2 — JSON строка** без нормализации в `niche_slug`
5. **Нет price benchmark** по нише/региону/периоду
6. **150 лотов** — недостаточно для статистики (нужно 30K+)

## Стиль кода

- Python 3.11+, type hints
- docstrings на русском
- Логирование через `logging` (не print)
- SQLAlchemy 2.0 стиль (mapped_column, Mapped)
- Даты в БД хранятся как строки `DD.MM.YYYY` (не datetime!)
- Цены: `float`, без центов

## Тесты

```bash
pytest                     # Пока нет тестов (только scraper/test_parser.py)
```

## Частые операции

```bash
# Собрать лоты (нужна сеть)
python scraper/collect_multi_regions.py

# Обогатить лоты деталями
python scraper/enrich_100_lots.py

# Загрузить в БД (нужна БД)
python db/init_database.py

# Запустить анализ (offline)
python analysis/run_audit_analysis.py

# Дашборд
streamlit run dashboard/app.py
```
