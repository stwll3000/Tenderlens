# Проблема с Supabase — Диагностика

**Дата:** 25.04.2026  
**Статус:** ❌ Подключение невозможно

---

## Проблема

Не удается подключиться к Supabase PostgreSQL ни с одним из connection strings.

### Протестированные варианты:

1. **Session pooler (aws-1, порт 5432)**
   ```
   postgresql://postgres.dnpjcxjjavzjmtfzlrip:***@aws-1-eu-north-1.pooler.supabase.com:5432/postgres
   ```
   Ошибка: `server closed the connection unexpectedly`

2. **Transaction pooler (aws-1, порт 6543)**
   ```
   postgresql://postgres.dnpjcxjjavzjmtfzlrip:***@aws-1-eu-north-1.pooler.supabase.com:6543/postgres
   ```
   Ошибка: `server closed the connection unexpectedly`

3. **Session pooler (aws-0, порт 5432)**
   ```
   postgresql://postgres.dnpjcxjjavzjmtfzlrip:***@aws-0-eu-north-1.pooler.supabase.com:5432/postgres
   ```
   Ошибка: `tenant/user not found`

4. **Transaction pooler (aws-0, порт 6543)**
   ```
   postgresql://postgres.dnpjcxjjavzjmtfzlrip:***@aws-0-eu-north-1.pooler.supabase.com:6543/postgres
   ```
   Ошибка: `tenant/user not found`

---

## Диагноз

### Вероятные причины:

1. **Проект был удален или приостановлен** (наиболее вероятно)
   - Project reference `dnpjcxjjavzjmtfzlrip` больше не существует
   - Проект мог быть удален из-за неактивности или вручную

2. **Изменился project reference**
   - После миграции или восстановления проекта
   - Новый project reference не совпадает со старым

3. **Проблемы с паролем**
   - Пароль был изменен
   - Пароль содержит специальные символы, требующие экранирования

4. **Проблемы с регионом**
   - Проект был перемещен в другой регион
   - `eu-north-1` больше не используется

---

## Решение

### Вариант 1: Получить актуальный connection string (рекомендуется)

1. Откройте [Supabase Dashboard](https://supabase.com/dashboard)
2. Найдите проект TenderLens (или создайте новый)
3. Перейдите в **Settings → Database**
4. Скопируйте актуальный **Connection string**
5. Обновите `.env` файл

### Вариант 2: Создать новый проект

Если проект был удален:

1. Откройте https://supabase.com/dashboard
2. Нажмите **New Project**
3. Укажите:
   - Name: `TenderLens`
   - Database Password: создайте надежный пароль
   - Region: `Europe North (Stockholm)` или ближайший
4. Дождитесь создания (~2 минуты)
5. Скопируйте connection string
6. Создайте таблицы (см. SETUP_SUPABASE.md)
7. Загрузите данные из JSON

### Вариант 3: Продолжить работу с JSON

Текущее состояние проекта:

✅ **6000 лотов** в JSON (`data/lots_multi_regions_6000_20260425.json`)  
✅ **Dashboard работает** с JSON  
✅ **Telegram-бот работает** с JSON  
✅ **Аналитика работает** с JSON  

PostgreSQL не критичен для текущей работы. Можно настроить позже.

---

## Текущее состояние данных

### Доступные JSON-файлы:

```
data/
├── lots_multi_regions_6000_20260425.json  (6000 лотов, 6.1 MB)
├── lots_enriched_100_20260425_212020.json (100 обогащенных лотов)
└── [другие файлы]
```

### Статистика:

- **Лотов:** 6,000
- **Регионов:** 12
- **Заказчиков:** 297
- **Общий объем:** 42 млрд ₽
- **Период:** 60 дней

---

## Рекомендации

### Для продолжения работы:

1. **Используйте JSON** для текущей работы
   - Dashboard: `streamlit run dashboard/app.py`
   - Bot: `python bot/main.py`
   - Аналитика: работает с JSON

2. **Настройте Supabase позже** когда:
   - Нужна масштабируемость (>10,000 лотов)
   - Нужны сложные SQL-запросы
   - Нужна интеграция с другими сервисами

3. **Альтернативы Supabase:**
   - **SQLite** — локальная БД, простая настройка
   - **PostgreSQL локально** — через Docker
   - **Railway/Render** — бесплатный PostgreSQL хостинг
   - **Neon** — serverless PostgreSQL

---

## Следующие шаги

### Если нужен PostgreSQL:

1. Проверьте статус проекта в Supabase Dashboard
2. Получите новый connection string
3. Обновите `.env`
4. Создайте таблицы: `alembic upgrade head`
5. Загрузите данные: `python db/load_multi_regions.py`

### Если продолжаете с JSON:

1. ✅ Все работает из коробки
2. Запустите бота: `python bot/main.py`
3. Запустите dashboard: `streamlit run dashboard/app.py`
4. Продолжайте сбор данных: `python scraper/collect_multi_regions.py`

---

## Заключение

**Supabase подключение недоступно** с предоставленными credentials.

**Рекомендация:** Продолжайте работу с JSON. Для 6000 лотов этого достаточно. PostgreSQL можно настроить позже при необходимости масштабирования.

**Все основные функции работают:**
- ✅ Парсер
- ✅ Аналитика
- ✅ Dashboard
- ✅ Telegram-бот

---

**Для получения помощи:**
- Проверьте SETUP_SUPABASE.md
- Откройте https://supabase.com/dashboard
- Проверьте статус проекта
