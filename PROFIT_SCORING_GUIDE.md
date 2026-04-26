# TenderLens — Переход к Profit Scoring

Этот документ описывает изменения, внесённые в систему для превращения TenderLens из "дашборда статистики" в "движок поиска прибыльных лотов".

## Что изменилось

### 1. Новые таблицы БД

Добавлены 5 новых таблиц:
- **suppliers** — поставщики (юр. лица из протоколов)
- **lot_participations** — участие поставщика в лоте
- **lot_categories** — нормализованные категории (ОКПД2 → ниши)
- **price_benchmarks** — кэшированные benchmark'и по нише/региону
- **lot_scores** — результаты скоринга (Profit Score)

### 2. Обновлённые модели

**Lot** — добавлены поля:
- `niche_slug` — нормализованная ниша
- `tz_text` — полный текст ТЗ для NLP

**Customer** — добавлены поля:
- `in_rnp` — флаг РНП
- `completed_contracts_12m` — число исполненных контрактов
- `avg_payment_delay_days` — средняя задержка платежа

### 3. Новые модули

**features/niche_mapping.py**
- Маппинг ОКПД2 → niche_slug
- 15 предопределённых ниш (медицина, IT, СИЗ, канцелярия и т.д.)

**analytics/benchmark.py**
- Расчёт price benchmark по нише/региону/периоду
- Медианные цены, снижение, среднее число поставщиков

**analytics/profit.py**
- Главный модуль: расчёт Profit Score (0-100)
- 6 компонентов: margin, competition, captive, timing, spec_purity, customer_health
- Веса: margin 30%, competition 25%, captive 15%, остальные по 10%

**analytics/competition_v2.py**
- Правильный расчёт конкуренции ПО ПОСТАВЩИКАМ (не по заказчикам)
- HHI, n_eff (эффективное число игроков)
- Интерпретация: "Монополия", "Олигополия", "Здоровая ниша", "Раздробленная"

**scoring/rigged_detector.py**
- Детектор "заточки" тендера
- 10 паттернов: редкий опыт, СРО, конкретные модели, запрет эквивалентов и т.д.

**scraper/fetch_protocols.py**
- Парсер протоколов итогов торгов
- Получает final_price, всех участников, ИНН поставщиков

**jobs/daily_scoring.py**
- Ежедневный скрипт для автоматизации
- Обновляет ниши, benchmarks, протоколы, скоринг

## Как применить изменения

### Шаг 1: Применить миграцию БД

```bash
# Применить миграцию
alembic upgrade head

# Проверить, что таблицы созданы
python -c "from db.models import *; from db.connection import engine; print([t for t in Base.metadata.tables.keys()])"
```

### Шаг 2: Инициализировать категории

```bash
python -c "
from db.connection import get_session
from features.niche_mapping import init_niche_categories

with get_session() as session:
    count = init_niche_categories(session)
    print(f'Добавлено категорий: {count}')
"
```

### Шаг 3: Обновить niche_slug для существующих лотов

```bash
python -c "
from db.connection import get_session
from features.niche_mapping import update_lot_niches

with get_session() as session:
    updated = update_lot_niches(session)
    print(f'Обновлено лотов: {updated}')
"
```

### Шаг 4: Получить протоколы для завершённых лотов

```bash
python -c "
from db.connection import get_session
from scraper.fetch_protocols import fetch_protocols_for_lots

with get_session() as session:
    stats = fetch_protocols_for_lots(session, limit=100)
    print(f'Обработано: {stats}')
"
```

**ВАЖНО:** Этот шаг может занять много времени (2-5 секунд на лот). Для 1000 лотов — около 1 часа.

### Шаг 5: Рассчитать benchmarks

```bash
python -c "
from db.connection import get_session
from analytics.benchmark import compute_all_benchmarks

with get_session() as session:
    stats = compute_all_benchmarks(session, months=12)
    print(f'Benchmarks: {stats}')
"
```

### Шаг 6: Запустить скоринг

```bash
python -c "
from db.connection import get_session
from analytics.profit import score_all_lots

with get_session() as session:
    stats = score_all_lots(session)
    print(f'Скоринг: {stats}')
"
```

### Шаг 7: Настроить ежедневный запуск

**Linux/Mac (cron):**
```bash
# Открыть crontab
crontab -e

# Добавить строку (запуск каждый день в 06:00)
0 6 * * * cd /path/to/Tenderlens && /path/to/python jobs/daily_scoring.py
```

**Windows (Task Scheduler):**
```powershell
# Создать задачу через PowerShell
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\path\to\Tenderlens\jobs\daily_scoring.py" -WorkingDirectory "C:\path\to\Tenderlens"
$trigger = New-ScheduledTaskTrigger -Daily -At 6am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "TenderLens Daily Scoring" -Description "Ежедневный скоринг лотов"
```

## Как использовать новую аналитику

### Получить Profit Score для лота

```python
from db.connection import get_session
from db.models import Lot, Customer, LotScore
from analytics.profit import compute_profit_score

with get_session() as session:
    lot = session.query(Lot).filter_by(reg_number="0123456789012345678901234").first()
    customer = session.query(Customer).filter_by(url=lot.customer_url).first()
    
    score, signals = compute_profit_score(session, lot, customer)
    
    print(f"Profit Score: {score}/100")
    print(f"Компоненты:")
    print(f"  Margin: {signals.margin:.2f}")
    print(f"  Competition: {signals.competition:.2f}")
    print(f"  Captive: {signals.captive:.2f}")
    print(f"  Timing: {signals.timing:.2f}")
    print(f"  Spec purity: {signals.spec_purity:.2f}")
    print(f"  Customer health: {signals.customer_health:.2f}")
    print(f"Флаги: {', '.join(signals.flags)}")
```

### Получить топ-10 лотов по Profit Score

```python
from db.connection import get_session
from db.models import Lot, LotScore

with get_session() as session:
    top_lots = session.query(Lot, LotScore).join(LotScore).filter(
        Lot.status == "Подача заявок",
        Lot.niche_slug == "med-rashodniki",  # опционально: фильтр по нише
    ).order_by(LotScore.profit_score.desc()).limit(10).all()
    
    for lot, score in top_lots:
        print(f"{score.profit_score:.0f}/100 — {lot.object_name[:80]}")
        print(f"  НМЦ: {lot.initial_price:,.0f} ₽")
        print(f"  Заказчик: {lot.customer_name[:60]}")
        print(f"  Дедлайн: {lot.deadline_date}")
        print()
```

### Анализ конкуренции в нише

```python
from db.connection import get_session
from analytics.competition_v2 import supplier_concentration_in_niche

with get_session() as session:
    result = supplier_concentration_in_niche(
        session,
        niche_slug="med-rashodniki",
        region_code="77",  # Москва
        months=12
    )
    
    print(f"Концентрация в нише 'med-rashodniki' (Москва):")
    print(f"  HHI: {result['hhi']}")
    print(f"  Эффективное число игроков: {result['n_eff']}")
    print(f"  Интерпретация: {result['interpretation']}")
    print(f"  Топ-3 поставщика:")
    for s in result['top_suppliers'][:3]:
        print(f"    {s['name']}: {s['share_pct']}%")
```

### Детектор заточки

```python
from scoring.rigged_detector import analyze_lot_rigging

result = analyze_lot_rigging(
    object_name="Поставка медицинского оборудования Siemens ACUSON S2000",
    tz_text="Эквиваленты не допускаются. Требуется опыт работы не менее 7 лет..."
)

print(f"Purity Score: {result['purity_score']}")
print(f"Риск: {result['risk_level']}")
print(f"Рекомендация: {result['recommendation']}")
print(f"Найдено сигналов: {result['signals_found']}")
```

## Следующие шаги

### Краткосрочные (1-2 недели)
1. Запустить парсер протоколов для всех завершённых лотов
2. Накопить данные о поставщиках (минимум 1000 лотов с протоколами)
3. Откалибровать веса Profit Score на исторических данных

### Среднесрочные (1 месяц)
1. Добавить парсинг РНП (реестр недобросовестных поставщиков)
2. Интеграция с DaData/Контур.Фокус для обогащения ИНН
3. Расширить БД до 5+ регионов, 100k+ лотов

### Долгосрочные (2-3 месяца)
1. NLP: embeddings для семантического поиска лотов
2. ML-модель для калибровки весов (логистическая регрессия)
3. Telegram-бот для ежедневного дайджеста
4. FastAPI для отделения дашборда от БД

## KPI системы

Главные метрики успеха:
- **Precision дайджеста:** % лотов из дайджеста, в которых клиент реально участвовал
- **Recall дайджеста:** % выигранных клиентом лотов, которые попали в его дайджест
- **Покрытие протоколов:** % лотов со статусом "Завершено", для которых есть final_price

Целевые значения через 3 месяца:
- Покрытие протоколов: ≥80%
- Precision: ≥60%
- Recall: ≥80%

## Поддержка

При возникновении проблем:
1. Проверьте логи: `logs/daily_scoring.log`, `logs/protocol_scraper.log`
2. Убедитесь, что миграция применена: `alembic current`
3. Проверьте наличие данных: `SELECT COUNT(*) FROM lot_scores;`

---

**Дата создания:** 26 апреля 2026  
**Версия:** 1.0  
**Автор:** TenderLens Team
