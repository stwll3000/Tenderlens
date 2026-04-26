# Быстрый старт — День 2

## Что готово
✅ SQLAlchemy модели для БД (regions, customers, lots)
✅ Подключение к PostgreSQL через Supabase
✅ Alembic для миграций
✅ Загрузчик данных из JSON
✅ Скрипт автоинициализации БД
✅ Документация по настройке

## Что нужно сделать

### 1. Создать проект в Supabase (5 минут)
1. Перейти на https://supabase.com
2. Нажать "New Project"
3. Заполнить:
   - Name: `tenderlens`
   - Database Password: придумать и сохранить
   - Region: Frankfurt (ближайший к РФ)
4. Дождаться создания проекта (1-2 минуты)

### 2. Получить строку подключения (2 минуты)
1. Settings → Database
2. Connection string → URI
3. Скопировать строку вида:
   ```
   postgresql://postgres.[ref]:[password]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```
4. Заменить `[password]` на свой пароль

### 3. Настроить .env (1 минута)
```bash
copy .env.example .env
```

Открыть `.env` и вставить:
```env
DATABASE_URL=postgresql://postgres.xxxxx:your-password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

### 4. Запустить инициализацию (2 минуты)
```bash
python db/init_database.py
```

Скрипт автоматически:
- Проверит подключение
- Создаст таблицы
- Загрузит 3 региона
- Загрузит 150 лотов

### 5. Проверить результат
В Supabase Dashboard → Table Editor должны появиться таблицы:
- `regions` (3 записи)
- `customers` (~150 записей)
- `lots` (150 записей)

## Что дальше

### Масштабировать сбор данных
```bash
# Отредактировать scraper/fetch_lots.py
# Увеличить PAGES_PER_REGION с 1 до 50

python scraper/fetch_lots.py
python db/loader.py
```

Цель: собрать 1000+ лотов

### Начать аналитику
```bash
jupyter notebook notebooks/
```

Создать первый ноутбук для EDA (exploratory data analysis)

## Помощь

Подробная инструкция: `SETUP_DATABASE.md`

Проблемы с подключением:
```bash
python db/connection.py
```

Проверка данных:
```bash
python scraper/validate_data.py
```
