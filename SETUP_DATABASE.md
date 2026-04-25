# Настройка PostgreSQL (Supabase)

## Шаг 1: Создание проекта в Supabase

1. Перейдите на https://supabase.com и войдите/зарегистрируйтесь
2. Нажмите "New Project"
3. Заполните форму:
   - **Name**: tenderlens
   - **Database Password**: придумайте надёжный пароль (сохраните его!)
   - **Region**: выберите ближайший регион (например, Frankfurt для РФ)
   - **Pricing Plan**: Free (достаточно для старта)
4. Нажмите "Create new project" и дождитесь создания (1-2 минуты)

## Шаг 2: Получение строки подключения

1. В созданном проекте перейдите в **Settings** (иконка шестерёнки слева внизу)
2. Выберите **Database** в меню слева
3. Прокрутите до раздела **Connection string**
4. Выберите вкладку **URI**
5. Скопируйте строку подключения (она выглядит так):
   ```
   postgresql://postgres.[project-ref]:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```
6. Замените `[YOUR-PASSWORD]` на пароль, который вы создали в Шаге 1

## Шаг 3: Настройка .env файла

1. Скопируйте `.env.example` в `.env`:
   ```bash
   copy .env.example .env
   ```

2. Откройте `.env` и вставьте строку подключения:
   ```env
   DATABASE_URL=postgresql://postgres.xxxxx:your-password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```

## Шаг 4: Установка зависимостей

```bash
pip install -r requirements.txt
```

## Шаг 5: Проверка подключения

```bash
python db/connection.py
```

Вы должны увидеть:
```
✓ Подключение к БД успешно!
```

## Шаг 6: Создание таблиц

```bash
python -c "from db.connection import init_db; init_db()"
```

Или используйте Alembic (рекомендуется):
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Шаг 7: Загрузка данных

```bash
python db/loader.py
```

Вы должны увидеть:
```
============================================================
ЗАГРУЗКА ДАННЫХ В POSTGRESQL
============================================================

[1/3] Загрузка регионов...
✓ Регионы загружены

[2/3] Загрузка лотов...
Найдено 150 уникальных заказчиков
✓ Заказчики загружены
✓ Загружено: 150 лотов

[3/3] Статистика БД:
  regions: 3 записей
  customers: 150 записей
  lots: 150 записей

============================================================
✓ ЗАГРУЗКА ЗАВЕРШЕНА УСПЕШНО
============================================================
```

## Проверка данных в Supabase

1. Вернитесь в Supabase Dashboard
2. Перейдите в **Table Editor** (иконка таблицы слева)
3. Вы должны увидеть 3 таблицы: `regions`, `customers`, `lots`
4. Откройте таблицу `lots` и проверьте данные

## Troubleshooting

### Ошибка: "DATABASE_URL не найден"
- Убедитесь, что файл `.env` создан и содержит `DATABASE_URL`
- Проверьте, что `.env` находится в корне проекта

### Ошибка: "connection refused" или "timeout"
- Проверьте правильность строки подключения
- Убедитесь, что пароль указан корректно
- Проверьте интернет-соединение

### Ошибка: "password authentication failed"
- Пароль в `DATABASE_URL` должен совпадать с паролем из Шага 1
- Если забыли пароль, сбросьте его в Settings > Database > Reset database password

### Ошибка: "No module named 'alembic'"
- Установите зависимости: `pip install -r requirements.txt`
- Если установка долгая, используйте прямое создание таблиц через `init_db()`
