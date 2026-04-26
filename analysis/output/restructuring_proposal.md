# TenderLens — Реструктуризация проекта для Claude Code

## 1. Проблемы текущей структуры

### 1.1. Мусор в корне репозитория (16 файлов, ~4000 строк)

В корне лежат **16 файлов-журналов и промптов**, которые не являются кодом:

```
DAY1_SUMMARY.md          (55 строк)
DAY2_FINAL.md            (129)
DAY2_SUMMARY.md          (162)
DAY3_SUMMARY.md          (210)
DAY4_COMPLETE.md         (248)
DAY4_FINAL.md            (260)
DAY4_FINAL_REPORT.md     (314)
DAY4_FINAL_SUMMARY.md    (160)
DAY4_RECAP.md            (138)
DAY4_SCALING.md          (206)
DAY4_SUMMARY.md          (259)
DAY4_SUMMARY_FINAL.md    (151)
DAY5_COMPLETE.md         (152)
DAY5_REPORT.md           (301)
DAY5_SUMMARY.md          (43)
TENDERLENS_PLAN.md       (218)
TENDERLENS_PROMPT.md     (201)
TENDERLENS_PROMPT_DAY4.md (340)
TENDERLENS_PROMPT_DAY5.md (435)
QUICKSTART.md            (90)
QUICKSTART_DASHBOARD.md  (55)
SETUP_DATABASE.md        (121)
```

**Проблема:** Claude Code (и любой AI-агент) тратит токены на чтение файловой структуры корня. 22 нерелевантных файла = шум. Кроме того, 4030 строк журналов — это контекст, который агент может ошибочно считать инструкциями.

**Решение:** Перенести в `docs/journal/` и `docs/guides/`.

### 1.2. Дублирование скриптов (scraper/ и db/)

| Группа | Файлы | Проблема |
|--------|-------|----------|
| Парсеры | `fetch_lots.py` (365 стр) + `fetch_lots_enhanced.py` (367 стр) | Почти идентичный код, enhanced — версия с деталями. Оба живут параллельно |
| Сборщики | `collect_enhanced_data.py` + `collect_fast.py` + `collect_multi_regions.py` | 3 скрипта для одной задачи с разными параметрами. Можно объединить в один с CLI |
| Обогатители | `enrich_existing_lots.py` + `enrich_100_lots.py` | `enrich_100_lots.py` — обёртка на 35 строк вокруг `enrich_existing_lots.py` |
| Загрузчики | `loader.py` + `load_data_simple.py` + `load_multi_regions.py` + `load_remaining.py` | 4 скрипта загрузки с разными подходами (SQLAlchemy vs psycopg2 vs batch) |
| Проверки | `check_connection.py` + `check_stats.py` + `connection.py:test_connection()` | 3 способа проверить подключение |

**Итого:** ~15 файлов, из которых полезного уникального кода — на 5-6.

### 1.3. Отладочные файлы в репозитории

- `scraper/analyze_page_structure.py` — одноразовый скрипт исследования HTML
- `scraper/extract_fields.py` — одноразовый скрипт извлечения полей
- `scraper/test_detail_page.py` — тест одной страницы
- `scraper/test_enrichment.py` — тест обогащения
- `scraper/page_sample.html` — HTML-файл для отладки
- `data/test_page.html` — ещё один HTML для отладки
- `scripts/*.py` — 5 одноразовых скриптов анализа

### 1.4. connection.py крашится без .env

`db/connection.py` при импорте выбрасывает `ValueError` если нет `.env` с `DATABASE_URL`. Это ломает `db/__init__.py`, а через него — любой код, который делает `from db import ...`. Claude Code не сможет даже прочитать модели без настройки БД.

### 1.5. Нет точки входа и CLI

Нет `main.py`, `cli.py` или `Makefile`. Для каждой операции нужно помнить конкретный скрипт. Claude Code не имеет единого интерфейса для работы с проектом.

### 1.6. Нет pyproject.toml

Проект использует `requirements.txt` без версионирования, без entry points, без метаданных. Для Claude Code — невозможно определить Python-версию, entry points.

---

## 2. Предлагаемая структура

```
tenderlens/
├── CLAUDE.md                    # ✅ Контекст для AI-агентов (уже создан)
├── README.md                    # Обновлённый, без журнальных разделов
├── pyproject.toml               # Метаданные, зависимости, scripts
├── Makefile                     # Короткие команды для частых операций
├── .env.example
├── .gitignore
├── alembic.ini
│
├── src/                         # Основной код
│   ├── __init__.py
│   ├── scraper/                 # Парсинг (объединённый)
│   │   ├── __init__.py
│   │   ├── parser.py            # Единый ZakupkiScraper (merged fetch_lots*)
│   │   ├── enricher.py          # Обогащение лотов деталями
│   │   ├── regions.py           # Справочник регионов
│   │   └── cli.py               # CLI: `python -m src.scraper.cli --regions 77,50 --limit 100`
│   │
│   ├── db/                      # БД
│   │   ├── __init__.py
│   │   ├── models.py            # SQLAlchemy модели
│   │   ├── connection.py        # Engine (graceful без .env — возвращает None)
│   │   └── loader.py            # Единый загрузчик JSON → PostgreSQL
│   │
│   ├── analytics/               # Описательная аналитика (pandas)
│   │   ├── __init__.py
│   │   ├── pricing.py
│   │   ├── competition.py       # Исправленный HHI (по поставщикам, когда данные есть)
│   │   └── temporal.py
│   │
│   ├── scoring/                 # 🆕 Profit Score (из аудита)
│   │   ├── __init__.py
│   │   ├── profit.py            # Компоненты A-F + агрегатор
│   │   ├── benchmark.py         # Price benchmark по нише
│   │   ├── rigged_detector.py   # Детектор «заточки» (regex)
│   │   └── niche_mapping.py     # ОКПД2 → niche_slug
│   │
│   └── dashboard/               # Streamlit
│       └── app.py
│
├── alembic/                     # Миграции
│   ├── env.py
│   └── versions/
│
├── data/                        # Данные (gitignored)
├── notebooks/                   # Jupyter
│
├── docs/                        # Вся документация
│   ├── guides/
│   │   ├── QUICKSTART.md
│   │   ├── SETUP_DATABASE.md
│   │   └── DASHBOARD.md
│   ├── journal/                 # Дневники разработки
│   │   ├── DAY1_SUMMARY.md
│   │   ├── ...
│   │   └── DAY5_SUMMARY.md
│   └── plans/
│       ├── TENDERLENS_PLAN.md
│       └── AUDIT_ANALYSIS.md
│
└── tests/                       # Тесты
    ├── test_pricing.py
    ├── test_competition.py
    └── test_temporal.py
```

### Ключевые изменения:

| Что | Было | Стало |
|-----|------|-------|
| Журналы в корне | 16 файлов MD | `docs/journal/` |
| Парсеры | 2 парсера + 3 сборщика + 2 обогатителя | `scraper/parser.py` + `scraper/enricher.py` + `scraper/cli.py` |
| Загрузчики | 4 скрипта с разными подходами | `db/loader.py` (единый) |
| Проверки БД | 3 файла | `db/connection.py:test_connection()` (одна функция) |
| Отладочные | 7 файлов | Удалены (или в `.gitignore`) |
| Profit Score | Не существует | `scoring/` (новый пакет) |
| CLI | Нет | `Makefile` + `scraper/cli.py` |
| connection.py | Крашится без .env | Graceful degradation |

---

## 3. Makefile

```makefile
.PHONY: install scrape enrich load dashboard analyze test lint

install:
	pip install -r requirements.txt

scrape:
	python -m src.scraper.cli --regions 77,50,54 --limit 500

enrich:
	python -m src.scraper.cli --enrich --limit 100

load:
	python -m src.db.loader

dashboard:
	streamlit run src/dashboard/app.py

analyze:
	python analysis/run_audit_analysis.py

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/
```

---

## 4. Исправление connection.py (graceful без .env)

```python
# Текущее поведение (ЛОМАЕТ импорт):
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найден")  # ← крашит при импорте

# Предлагаемое:
DATABASE_URL = os.getenv("DATABASE_URL")
engine = None
SessionLocal = None

if DATABASE_URL:
    engine = create_engine(DATABASE_URL, ...)
    SessionLocal = sessionmaker(bind=engine)
else:
    import warnings
    warnings.warn("DATABASE_URL не задан. БД-функции недоступны.")
```

Это позволит `from db.models import Lot` работать без БД — критично для аналитики и тестов.

---

## 5. Приоритеты для реализации

### Фаза 0 — Минимальная оптимизация (1-2 часа)
1. ✅ Создать `CLAUDE.md` (уже сделано)
2. Перенести журналы в `docs/`
3. Исправить `connection.py` (graceful degradation)
4. Добавить `Makefile`

### Фаза 1 — Консолидация кода (2-4 часа)
5. Объединить `fetch_lots.py` + `fetch_lots_enhanced.py` → `scraper/parser.py`
6. Объединить `load_*.py` → единый `db/loader.py`
7. Удалить отладочные файлы
8. Добавить `pyproject.toml`

### Фаза 2 — Новые модули (из аудита, 1-2 дня)
9. Создать `scoring/niche_mapping.py` (ОКПД2 → niche_slug)
10. Создать `scoring/rigged_detector.py` (regex-паттерны)
11. Создать `scoring/profit.py` (Timing + Spec Purity — что уже работает)
12. Исправить HHI в `analytics/competition.py`
