# День 2 — База данных настроена и данные загружены (25.04.2026)

## ✅ Выполнено

### 1. Инфраструктура БД
- ✅ Созданы SQLAlchemy модели (regions, customers, lots)
- ✅ Настроено подключение к PostgreSQL через Supabase
- ✅ Настроен Alembic для миграций
- ✅ Создана документация (SETUP_DATABASE.md, QUICKSTART.md)

### 2. Решение проблем с Supabase Pooler
**Проблема:** Supabase pooler закрывает соединение при выполнении системных запросов (`pg_catalog.version()`, `current_schema()`)

**Решение:**
- Создание таблиц через прямой SQL (`db/create_tables.py`)
- Загрузка данных с переподключением для каждой операции (`db/load_data_simple.py`)
- Использование session pooler (порт 5432) вместо transaction pooler
- Добавление задержек между запросами (0.1 сек)

### 3. Загрузка данных
- ✅ 3 региона (Новосибирская область, Москва, Московская область)
- ✅ 96 уникальных заказчиков
- ✅ 150 лотов успешно загружено

### 4. Созданные скрипты
- `db/create_tables.py` — создание таблиц через SQL
- `db/load_data_simple.py` — загрузка данных с переподключением
- `db/load_remaining.py` — догрузка оставшихся лотов
- `db/check_stats.py` — проверка статистики БД

## 📊 Статистика БД

```
Регионов:     3
Заказчиков:   96
Лотов:        150

По законам:
  44-ФЗ:      125 (83%)
  223-ФЗ:     25 (17%)

По регионам:
  Новосибирская область: 50
  Московская область:    50
  Москва:                50
```

## 🔧 Технические детали

### Строка подключения
```
postgresql://postgres.dnpjcxjjavzjmtfzlrip:[password]@aws-1-eu-north-1.pooler.supabase.com:5432/postgres
```

### Структура таблиц

**regions:**
- id, code (UNIQUE), name, created_at

**customers:**
- id, name, url (UNIQUE), inn, kpp, created_at, updated_at

**lots:**
- id, reg_number (UNIQUE), url, law, purchase_method, status
- object_name, customer_name, customer_url
- initial_price, final_price, price_reduction_pct
- region_code, region_name, scraped_at
- created_at, updated_at
- Индексы: reg_number, law, status, customer_url, initial_price, region_code, scraped_at

## 🎯 Следующие шаги (День 3)

### 1. Масштабирование сбора данных
- Увеличить PAGES_PER_REGION с 1 до 50 в `scraper/fetch_lots.py`
- Собрать 1000+ лотов
- Настроить автоматическую загрузку в БД

### 2. Начало аналитики
- Создать Jupyter notebook для EDA
- Реализовать расчёт снижения цены (α)
- Реализовать расчёт конкурентности ниш
- Анализ распределения по категориям

### 3. Оптимизация работы с БД
- Рассмотреть использование Direct Connection (требует IPv6)
- Или настроить VPN/прокси для стабильного подключения
- Оптимизировать batch-вставки

## ⏱️ Время выполнения
**~3 часа** (настройка Supabase, решение проблем с pooler, загрузка данных)

## 📈 Прогресс проекта
**Фаза 1 (Сбор и структурирование данных): 70%**
- ✅ Парсер данных (150 лотов)
- ✅ Валидация данных
- ✅ Модели БД
- ✅ Подключение к PostgreSQL
- ✅ Загрузка данных в БД
- ⏳ Масштабирование сбора до 1000+ лотов
- ⏳ Автоматизация обновления данных

## 🔗 Полезные команды

```bash
# Проверка статистики БД
python db/check_stats.py

# Создание таблиц
python db/create_tables.py

# Загрузка данных
python db/load_data_simple.py

# Догрузка оставшихся лотов
python db/load_remaining.py

# Проверка подключения
python -c "import sys; sys.path.insert(0, '.'); from db.connection import test_connection; test_connection()"
```

## 💡 Уроки

1. **Supabase Pooler ограничения:** Session pooler блокирует некоторые системные запросы, требуется обход через прямой SQL
2. **Переподключение:** Для стабильной работы с pooler нужно переподключаться после каждой операции
3. **IPv6 vs IPv4:** Direct connection работает только через IPv6, pooler — через IPv4
4. **Задержки:** Небольшие задержки (0.1 сек) между запросами повышают стабильность

## ✅ Результат
База данных успешно развёрнута и заполнена. Готова к аналитике и масштабированию!
