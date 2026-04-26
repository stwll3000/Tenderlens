# TenderLens — Аудит аналитики и план перехода к поиску прибыльных лотов

> Цель документа: жёстко оценить текущую аналитику, показать гэпы, дать конкретные изменения (схема БД, метрики, формулы, код, архитектура), которые превратят TenderLens из «дашборда статистики» в «движок поиска прибыльных лотов».

---

## 1. Что есть сейчас (объективная оценка)

### 1.1. Данные
**Схема БД** (<ref_file file="/home/ubuntu/repos/Tenderlens/db/models.py" />): три таблицы — `regions`, `customers`, `lots`. В `lots` хранятся: НМЦ, регион, закон (44/223), статус, ОКПД2 (как JSON-строка), даты публикации/дедлайна, поля `final_price` / `price_reduction_pct` / `participants_count`.

**Объём:** ~150 лотов из 3 регионов за 3 месяца. Это меньше, чем нужно для любой статистической работы (для baseline по нише требуется минимум 3–5 тыс. лотов в каждой нише за 12 месяцев).

### 1.2. Аналитические модули

| Модуль | Что делает | Качество |
|---|---|---|
| `analytics/pricing.py` | Распределение НМЦ, перцентили, IQR-выбросы, формула α = (НМЦ − final)/НМЦ | Корректно как описательная статистика; ничего не говорит о прибыльности конкретного лота. |
| `analytics/competition.py` | HHI **по заказчикам**, топ-заказчики, разрезы по региону/закону/статусу | **HHI считается не в ту сторону** — для прибыльности важна концентрация **поставщиков** в нише, а не заказчиков. |
| `analytics/temporal.py` | Дедлайн-распределение, дни недели, сезонность | OK, но не превращено в фичу скоринга. |
| `dashboard/app.py` | Streamlit с фильтрами и 5 вкладками описательной статистики | Это **smart-каталог**, а не инструмент поиска лотов. |

### 1.3. Главные проблемы текущей аналитики (по приоритету)

1. **Нет поставщиков и победителей.** В БД нет таблицы `suppliers`, нет `protocols/awards`. Без этого невозможно посчитать ни winrate, ни «captive» заказчиков, ни реальную плотность конкуренции.
2. **`final_price` и `participants_count` почти всегда NULL.** Парсер не насыщает протоколы итогов. Значит метрика α (price reduction) считается на крошечной выборке и бесполезна как ориентир.
3. **HHI считается по заказчикам** (`market_concentration` в <ref_snippet file="/home/ubuntu/repos/Tenderlens/analytics/competition.py" lines="93-133" />). Для МСБ-поставщика, который ищет «куда вписаться», нужна обратная метрика: HHI **по поставщикам в нише** + «эффективное число игроков» N_eff = 1/Σ(s_i²).
4. **`participants_count` ≠ конкуренция.** Это число **заявок**, а не уникальных юр. лиц (один и тот же поставщик может подавать несколько заявок через дочки). Кроме того, на НМЦ важна не сама цифра, а её динамика по нише.
5. **Нет нормализации товара/услуги.** `object_name` хранится как сырой текст. ОКПД2 — JSON-строка. Никакой кластеризации, никаких embeddings → невозможно сказать «вот 50 лотов про лазерные картриджи за последний год». Без этого нельзя посчитать price benchmark.
6. **Нет price benchmark.** Главный сигнал маржи — насколько НМЦ выше рыночной медианы по ОКПД2/нише/региону. Сейчас этого расчёта нет.
7. **Нет `Profit Score`.** Все модули — описательные. Нет агрегированной метрики «стоит ли вписываться в этот лот».
8. **Нет детектора «заточки»** под конкретного поставщика (СРО редкого типа, конкретные модели в ТЗ, узкий опыт работы, нереальные сроки).
9. **Нет ИНН заказчика → ЕГРЮЛ → платёжная дисциплина.** Поле `customer.inn` есть в схеме, но не парсится и не обогащается.
10. **Нет «повторяемости» заказчика.** Если заказчик каждый квартал делает похожий лот — это золото, но эта связь не построена.
11. **Нет push/digest/alerts.** Stack — только Streamlit. Главный продуктовый канал (Telegram-дайджест по утрам) отсутствует.
12. **Объём данных слишком мал.** 150 лотов — это демо. Нужно минимум 50–100 тыс. лотов по нише за 12 месяцев.

---

## 2. Что значит «прибыльный лот» — определимся с метрикой

Прибыльный лот для МСБ-поставщика — это лот, для которого одновременно:

| Критерий | Что считаем | Где взять |
|---|---|---|
| **(A) НМЦ выше медианы рынка** | НМЦ лота ÷ медиана НМЦ для того же ОКПД2/региона/типа за 12 мес. >1.10 | history БД + price benchmark |
| **(B) Низкая конкуренция** | Среднее число уникальных поставщиков в аналогичных лотах <5 | history БД + supplier participation table |
| **(C) Не «captive»** | У заказчика нет одного «своего» поставщика, забирающего >60% контрактов | customer_supplier history |
| **(D) Реальные сроки** | Срок подачи 5–14 дней (срочные лоты часто с малой конкуренцией, но рискованны; «нормальные» — оптимум) | already есть в БД |
| **(E) Чистое ТЗ** | Нет признаков заточки: редкая СРО, конкретные модели, нерелевантный опыт | NLP/regex на `object_name` + текст ТЗ |
| **(F) Платёжеспособный заказчик** | Заказчик не в РНП, есть исполненные контракты, нет арбитражей с поставщиками | ИНН → ЕГРЮЛ + ЕИС |
| **(G) Подходит под профиль клиента** | ОКПД2 пересекается с тем, что клиент уже делал, регион в радиусе логистики | personalization layer |

**Profit Score** = взвешенная агрегация (A)…(G). Именно этого метрика нет ни в одном модуле. Это и есть главное изменение.

---

## 3. Что менять — конкретно

### 3.1. Изменения в схеме БД (новые таблицы)

```python
# Новый файл: db/models.py — добавить эти модели

class Supplier(Base):
    """Поставщики (юр. лица из протоколов)."""
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inn: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    name: Mapped[str] = mapped_column(Text)
    kpp: Mapped[str | None] = mapped_column(String(9))
    region_code: Mapped[str | None] = mapped_column(String(2), index=True)
    is_smp: Mapped[bool] = mapped_column(default=False)  # СМП/СОНКО
    in_rnp: Mapped[bool] = mapped_column(default=False)  # реестр недобросовестных
    rnp_until: Mapped[datetime | None] = mapped_column(DateTime)
    egrul_revenue: Mapped[float | None] = mapped_column(Float)  # выручка
    egrul_employees: Mapped[int | None] = mapped_column(Integer)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime)

class LotParticipation(Base):
    """Участие поставщика в конкретном лоте (заявка)."""
    __tablename__ = "lot_participations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lot_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lots.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    bid_price: Mapped[float | None] = mapped_column(Float)  # цена заявки
    is_winner: Mapped[bool] = mapped_column(default=False)
    rank: Mapped[int | None] = mapped_column(Integer)  # место в торгах
    rejected: Mapped[bool] = mapped_column(default=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('lot_id', 'supplier_id'),)

class LotCategory(Base):
    """Нормализованные категории лотов (наша таксономия поверх ОКПД2)."""
    __tablename__ = "lot_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    okpd2_prefix: Mapped[str] = mapped_column(String(20), index=True)
    niche_slug: Mapped[str] = mapped_column(String(100), index=True)  # 'med-rashodniki'
    name: Mapped[str] = mapped_column(String(255))

class PriceBenchmark(Base):
    """Кэшированные benchmark'и по нише/региону/периоду."""
    __tablename__ = "price_benchmarks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    niche_slug: Mapped[str] = mapped_column(String(100), index=True)
    region_code: Mapped[str | None] = mapped_column(String(2))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    sample_size: Mapped[int] = mapped_column(Integer)
    median_initial_price: Mapped[float] = mapped_column(Float)
    median_final_price: Mapped[float | None] = mapped_column(Float)
    median_alpha: Mapped[float | None] = mapped_column(Float)  # медианное снижение
    avg_unique_suppliers: Mapped[float | None] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime)

class LotScore(Base):
    """Результат скоринга лота (Profit Score)."""
    __tablename__ = "lot_scores"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    lot_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lots.id"), unique=True, index=True)
    profit_score: Mapped[float] = mapped_column(Float, index=True)  # 0..100
    margin_signal: Mapped[float] = mapped_column(Float)  # компонент A
    competition_signal: Mapped[float] = mapped_column(Float)  # B
    captive_signal: Mapped[float] = mapped_column(Float)  # C
    timing_signal: Mapped[float] = mapped_column(Float)  # D
    spec_purity_signal: Mapped[float] = mapped_column(Float)  # E
    customer_health: Mapped[float] = mapped_column(Float)  # F
    flags_json: Mapped[str] = mapped_column(Text)  # ["captive", "premium_nmc", ...]
    computed_at: Mapped[datetime] = mapped_column(DateTime)
```

Также — поправить существующие поля в `Lot`:
- `okpd2_codes`: `Text` → нормализованная JSONB колонка (если PostgreSQL) или связь many-to-many с `lot_categories`.
- Добавить `niche_slug: str | None` (денормализованно для скорости фильтрации).
- Добавить `tz_text: Text | None` — полный текст ТЗ (для NLP).

### 3.2. Парсер — что добавить

| Что | Зачем | Сложность |
|---|---|---|
| **Протоколы итогов** (`itogPrt`, `protocolsTab`) | Получать `final_price`, `winner_inn`, всех участников и их ставки | Средняя (есть открытые URL по reg_number) |
| **Полный ТЗ / документация** (вложения PDF/DOCX) | NLP на «заточку» | Высокая (PDF-парсинг) |
| **РНП** (открытый реестр) | Флаг `in_rnp` для поставщиков | Низкая (отдельный реестр на zakupki.gov.ru) |
| **DaData / Контур.Фокус API** для ИНН → выручка, статус | Customer health и supplier scoring | Низкая (платное API) |
| **Жалобы ФАС** на закупку | Признак «нечистого» лота | Средняя |

**Главное:** парсер сейчас собирает «карточки лотов», но не итоги. Без итогов аналитика прибыльности невозможна. Это **приоритет №1**.

### 3.3. Новый модуль `analytics/profit.py` — Profit Score

Это центральная новая фича. Привожу полную реализацию ядра.

```python
"""
analytics/profit.py — расчёт Profit Score лота.
"""
from dataclasses import dataclass, field
import math
import pandas as pd
from sqlalchemy.orm import Session
from db.models import Lot, LotParticipation, PriceBenchmark, Supplier

@dataclass
class ProfitSignals:
    margin: float = 0.0          # A: 0..1 (1 = НМЦ сильно выше медианы)
    competition: float = 0.0     # B: 0..1 (1 = низкая конкуренция)
    captive: float = 0.0         # C: 0..1 (1 = НЕ captive)
    timing: float = 0.0          # D: 0..1 (1 = здоровые сроки)
    spec_purity: float = 0.0     # E: 0..1 (1 = ТЗ чистое)
    customer_health: float = 0.0 # F: 0..1 (1 = заказчик здоров)
    flags: list[str] = field(default_factory=list)

# Веса (откалибровать на исторических winrate-данных)
WEIGHTS = {
    "margin":          0.30,
    "competition":     0.25,
    "captive":         0.15,
    "timing":          0.10,
    "spec_purity":     0.10,
    "customer_health": 0.10,
}

def _sigmoid(x: float, k: float = 1.0) -> float:
    """Гладкое преобразование в 0..1."""
    return 1.0 / (1.0 + math.exp(-k * x))

# ---------- A. Margin signal (НМЦ vs benchmark) ----------
def margin_signal(lot: Lot, benchmark: PriceBenchmark | None) -> tuple[float, list[str]]:
    flags = []
    if not benchmark or not benchmark.median_initial_price:
        return 0.5, ["no_benchmark"]
    ratio = lot.initial_price / benchmark.median_initial_price
    # ratio=1.0 → 0.5; ratio=1.30 → ~0.95; ratio=0.7 → ~0.05
    score = _sigmoid((ratio - 1.0) * 5.0)
    if ratio > 1.20: flags.append("premium_nmc")
    if ratio < 0.80: flags.append("underpriced")
    return score, flags

# ---------- B. Competition signal ----------
def competition_signal(
    avg_unique_suppliers_in_niche: float | None,
    participants_count: int | None,
) -> tuple[float, list[str]]:
    flags = []
    # Используем то, что есть: среднее по нише, или текущий participants_count
    n = avg_unique_suppliers_in_niche or (participants_count or 5)
    if n <= 1.5:
        flags.append("monopoly_risk")  # подозрительно: 1 участник
        return 0.30, flags
    if n <= 3:
        return 0.90, ["low_competition"]
    if n <= 5:
        return 0.65, []
    if n <= 10:
        return 0.35, []
    return 0.10, ["crowded"]

# ---------- C. Captive customer detector ----------
def captive_signal(session: Session, customer_id: int, niche_slug: str) -> tuple[float, list[str]]:
    """1.0 = нет captive поставщика; 0.0 = заказчик 'свой' для конкретного поставщика."""
    rows = session.execute("""
        SELECT lp.supplier_id, COUNT(*) AS wins
        FROM lot_participations lp
        JOIN lots l ON l.id = lp.lot_id
        WHERE lp.is_winner = TRUE
          AND l.customer_id = :cid
          AND l.niche_slug = :niche
          AND l.published_date >= NOW() - INTERVAL '12 months'
        GROUP BY lp.supplier_id
        ORDER BY wins DESC
        LIMIT 5
    """, {"cid": customer_id, "niche": niche_slug}).fetchall()
    if not rows:
        return 0.7, ["no_history"]
    total = sum(r.wins for r in rows)
    top_share = rows[0].wins / total if total else 0
    if top_share >= 0.8:
        return 0.05, ["captive_customer"]
    if top_share >= 0.6:
        return 0.30, ["likely_captive"]
    if top_share >= 0.4:
        return 0.60, []
    return 0.95, []

# ---------- D. Timing signal ----------
def timing_signal(deadline_days: int | None, law: str) -> tuple[float, list[str]]:
    """Оптимум по 44-ФЗ: 7–14 дней (электронный аукцион). <5 — слишком рискованно, >30 — много конкурентов."""
    if deadline_days is None:
        return 0.5, []
    if deadline_days < 3:
        return 0.20, ["rushed"]
    if deadline_days < 7:
        return 0.85, ["short_window_low_competition"]  # часто меньше участников
    if deadline_days <= 14:
        return 0.95, []
    if deadline_days <= 30:
        return 0.65, []
    return 0.40, ["long_window_more_competition"]

# ---------- E. Spec purity (детектор «заточки») ----------
RIGGED_PATTERNS = [
    (r"опыт.*не\s*менее\s*([5-9]|1[0-9])\s*(лет|года)", "long_experience_required"),
    (r"наличи[ея]\s*св-?ва?\s*СРО", "rare_sro"),
    (r"конкретн[аы][ея]?\s*модел[ьи]", "specific_model"),
    (r"производител[ья]\s*[A-ZА-Я][\w-]+", "specific_manufacturer"),
    (r"эквивалент\s*не\s*допуск", "no_equivalent"),
    (r"должен\s*находиться\s*в\s*([\w\s-]+)\s*(области|крае|округе)", "geo_lock"),
]

def spec_purity_signal(object_name: str, tz_text: str | None) -> tuple[float, list[str]]:
    import re
    text = (object_name + "\n" + (tz_text or "")).lower()
    flags = []
    penalties = 0
    for pattern, flag in RIGGED_PATTERNS:
        if re.search(pattern, text):
            flags.append(flag)
            penalties += 1
    if penalties == 0:
        return 0.95, []
    if penalties == 1:
        return 0.55, flags
    if penalties == 2:
        return 0.25, flags
    return 0.05, flags + ["likely_rigged"]

# ---------- F. Customer health ----------
def customer_health_signal(customer) -> tuple[float, list[str]]:
    flags = []
    if getattr(customer, "in_rnp", False):
        return 0.0, ["customer_in_rnp"]
    score = 0.5
    # +0.2 если есть исполненные контракты за 12 мес
    if (customer.completed_contracts_12m or 0) > 5:
        score += 0.2
    # +0.2 если средняя задержка платежа < 30 дней
    avg_delay = getattr(customer, "avg_payment_delay_days", None)
    if avg_delay is not None and avg_delay < 30:
        score += 0.2
    elif avg_delay and avg_delay > 60:
        score -= 0.2
        flags.append("late_payer")
    return max(0.0, min(1.0, score)), flags

# ---------- Aggregator ----------
def compute_profit_score(
    session: Session,
    lot: Lot,
    benchmark: PriceBenchmark | None,
    niche_avg_suppliers: float | None,
    customer,
) -> tuple[float, ProfitSignals]:
    sig = ProfitSignals()
    sig.margin, f1 = margin_signal(lot, benchmark)
    sig.competition, f2 = competition_signal(niche_avg_suppliers, lot.participants_count)
    sig.captive, f3 = captive_signal(session, customer.id, lot.niche_slug or "")
    sig.timing, f4 = timing_signal(_deadline_days(lot), lot.law)
    sig.spec_purity, f5 = spec_purity_signal(lot.object_name, getattr(lot, "tz_text", None))
    sig.customer_health, f6 = customer_health_signal(customer)
    sig.flags = f1 + f2 + f3 + f4 + f5 + f6

    score = sum(getattr(sig, k) * w for k, w in WEIGHTS.items()) * 100
    # Hard veto: customer in РНП — score 0
    if "customer_in_rnp" in sig.flags:
        score = 0
    return round(score, 1), sig

def _deadline_days(lot: Lot) -> int | None:
    from datetime import datetime
    try:
        pub = datetime.strptime(lot.published_date, "%d.%m.%Y")
        dead = datetime.strptime(lot.deadline_date, "%d.%m.%Y")
        d = (dead - pub).days
        return d if d >= 0 else None
    except Exception:
        return None
```

**Откуда берутся веса?** На старте — из экспертной оценки (как выше). Через 3–6 месяцев, когда накопится 1000+ скорингов с фактическим исходом (выиграл клиент / нет, какая была маржа), — переподобрать веса логистической регрессией на бинарной таргетной переменной «выгодно_было_участвовать».

### 3.4. Новый модуль `analytics/benchmark.py` — Price Benchmark

```python
"""
analytics/benchmark.py — расчёт price benchmark по нише.
"""
import pandas as pd
from sqlalchemy.orm import Session
from datetime import date, timedelta
from db.models import Lot, PriceBenchmark

def compute_niche_benchmark(
    session: Session,
    niche_slug: str,
    region_code: str | None = None,
    months: int = 12,
) -> PriceBenchmark | None:
    today = date.today()
    start = today - timedelta(days=30 * months)
    q = session.query(Lot).filter(
        Lot.niche_slug == niche_slug,
        Lot.published_date_dt >= start,
    )
    if region_code:
        q = q.filter(Lot.region_code == region_code)
    df = pd.read_sql(q.statement, session.bind)
    if len(df) < 30:
        return None  # выборка слишком мала
    bench = PriceBenchmark(
        niche_slug=niche_slug,
        region_code=region_code,
        period_start=start,
        period_end=today,
        sample_size=len(df),
        median_initial_price=float(df["initial_price"].median()),
        median_final_price=float(df["final_price"].median()) if df["final_price"].notna().sum() > 10 else None,
        median_alpha=float(df["price_reduction_pct"].median()) if df["price_reduction_pct"].notna().sum() > 10 else None,
    )
    session.add(bench); session.commit()
    return bench
```

Запускать ежедневно cron'ом по всем нишам в БД.

### 3.5. Новый модуль `analytics/competition_v2.py` — правильная конкуренция

Заменить `market_concentration` (по заказчикам) на функции для **поставщиков**:

```python
def supplier_concentration_in_niche(
    session: Session, niche_slug: str, region_code: str | None = None, months: int = 12
) -> dict:
    """HHI по поставщикам в нише: показывает, насколько 'занят' рынок."""
    rows = session.execute("""
        SELECT s.inn, COUNT(*) AS wins
        FROM lot_participations lp
        JOIN lots l ON l.id = lp.lot_id
        JOIN suppliers s ON s.id = lp.supplier_id
        WHERE lp.is_winner = TRUE
          AND l.niche_slug = :niche
          AND (:region IS NULL OR l.region_code = :region)
          AND l.published_date_dt >= NOW() - (INTERVAL '1 month' * :months)
        GROUP BY s.inn
    """, {"niche": niche_slug, "region": region_code, "months": months}).fetchall()
    total = sum(r.wins for r in rows) or 1
    shares = [(r.inn, r.wins / total) for r in rows]
    hhi = sum((s * 100) ** 2 for _, s in shares)  # 0..10000
    n_eff = (1 / sum(s ** 2 for _, s in shares)) if shares else 0
    top1 = max((s for _, s in shares), default=0) * 100
    return {
        "hhi": round(hhi, 1),
        "n_eff": round(n_eff, 2),  # эффективное число игроков
        "top1_share_pct": round(top1, 1),
        "interpretation": _interpret(hhi, n_eff),
    }

def _interpret(hhi: float, n_eff: float) -> str:
    if n_eff < 2:    return "Монополия — не лезть"
    if n_eff < 4:    return "Олигополия — высокий риск 'своих'"
    if n_eff < 10:   return "Здоровая ниша для МСБ"
    return "Раздробленная — низкая маржа из-за демпинга"
```

**Метрика n_eff (эффективное число игроков)** для МСБ полезнее HHI: «в этой нише реально 3.2 серьёзных конкурента» — это понятно сразу.

### 3.6. Нормализация ниши: ОКПД2 + текстовая кластеризация

**Шаг 1 (быстро, неделя):** ОКПД2-маппинг. ОКПД2 — иерархический, первые 2 цифры = раздел (например `21` — фарма), 3 цифры = группа. Сделать таблицу `lot_categories` со словарём ваших ниш:

```python
NICHE_MAP = {
    "med-rashodniki":   ["32.50.13", "32.50.21", "32.50.41"],
    "it-oborudovanie":  ["26.20", "27.20"],
    "siz":              ["14.12", "32.99.11"],
    "kanc":             ["17.23", "32.99.12"],
    "klining-uslugi":   ["81.21", "81.22"],
    # ...
}
```

При загрузке лота → берём `okpd2_codes`, сопоставляем по prefix → пишем `niche_slug`.

**Шаг 2 (через месяц):** sentence-embeddings. На многоязычной модели типа `intfloat/multilingual-e5-base` (≈ 280 МБ, работает на CPU), проиндексировать `object_name + первая страница ТЗ`. Результат — кластеризация и semantic search «найди мне лоты, похожие на этот выигранный мной».

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("intfloat/multilingual-e5-base")
embeddings = model.encode([f"passage: {x}" for x in df["object_name"]])
# Хранить в pgvector / Qdrant; для 100к лотов хватит локального FAISS.
```

Это даёт качественный скачок: вместо «фильтра по ОКПД2 21.20.10» вы говорите «найди тендеры, похожие на тендер X», и движок возвращает релевантное независимо от того, каким ОКПД2 заказчик его пометил.

### 3.7. Архитектурные изменения

**Разделение слоёв** (сейчас всё в одной плоскости):

```
ingestion/         # Парсеры + ETL
  scrapers/        
    fetch_lots.py
    fetch_protocols.py    # НОВОЕ — итоги торгов
    fetch_rnp.py          # НОВОЕ
    fetch_egrul.py        # НОВОЕ — DaData/Контур.Фокус
  loaders/
  
storage/           # БД (бывш. db/)
  models.py
  migrations/
  
features/          # НОВОЕ — feature store
  benchmarks.py    # PriceBenchmark builder
  embeddings.py    # NLP для object_name/ТЗ
  niche_mapping.py # ОКПД2 → niche_slug
  
scoring/           # НОВОЕ — заменяет analytics в роли «принятия решений»
  profit.py        # Profit Score
  competition.py   # n_eff, supplier concentration
  rigged_detector.py  # NLP detection «заточки»
  
analytics/         # Описательная статистика для дашборда
  pricing.py
  temporal.py
  
api/               # НОВОЕ — REST API
  main.py          # FastAPI
  routes/
    lots.py
    scoring.py
    digest.py
    
delivery/          # НОВОЕ — каналы доставки
  telegram_bot.py  # daily digest
  email_digest.py
  webhooks.py
  
dashboard/         # streamlit, как сейчас, но потребляет API
  app.py
  
jobs/              # НОВОЕ — оркестрация
  scheduler.py     # APScheduler / cron
  pipelines/
    daily_ingestion.py
    daily_scoring.py
    daily_digest.py
```

**Ключевое:** скоринг — это **отдельный слой**, а не вкладка в дашборде. Он публикует score в БД, всё остальное (digest, дашборд, API) — потребляет.

### 3.8. Daily digest — главный продуктовый артефакт

```python
# delivery/telegram_bot.py
from aiogram import Bot
from sqlalchemy.orm import Session
from storage.models import Lot, LotScore

async def daily_digest_for_client(session: Session, client_id: int, bot: Bot):
    pref = session.get(ClientPreference, client_id)
    rows = session.query(Lot, LotScore).join(LotScore).filter(
        Lot.niche_slug.in_(pref.niches),
        Lot.region_code.in_(pref.regions),
        Lot.initial_price.between(pref.min_price, pref.max_price),
        LotScore.profit_score >= pref.min_score,
        Lot.status == "Подача заявок",
    ).order_by(LotScore.profit_score.desc()).limit(10).all()

    if not rows:
        return
    text = "🎯 *Топ-10 лотов на сегодня*\n\n"
    for lot, sc in rows:
        text += (
            f"*{sc.profit_score:.0f}/100* — {lot.object_name[:80]}\n"
            f"  💰 НМЦ: {lot.initial_price:,.0f} ₽\n"
            f"  🏢 {lot.customer_name[:60]}\n"
            f"  ⏱ Дедлайн: {lot.deadline_date}\n"
            f"  🚩 Сигналы: {', '.join(json.loads(sc.flags_json)[:3]) or '—'}\n"
            f"  🔗 [Открыть лот]({lot.url})\n\n"
        )
    await bot.send_message(pref.telegram_chat_id, text, parse_mode="Markdown")
```

Запускать каждое утро в 08:00 МСК через APScheduler.

### 3.9. Что **выкинуть** из дашборда

| Сейчас в `dashboard/app.py` | Решение |
|---|---|
| Вкладка «Распределения» (гистограммы НМЦ) | Оставить, но сжать в 1 график. Клиенты на это не смотрят. |
| Вкладка «Временной анализ» (дни недели, сезонность) | Убрать из main view, переместить в «Аналитика рынка» (admin). |
| Топ-10 заказчиков по объёму закупок | Оставить только в режиме «исследование ниши». В digest не нужно. |

**Добавить в дашборд:**
- Вкладка **«Лоты под меня»** (отсортирована по Profit Score) — это главный экран.
- Вкладка **«Конкретный лот»** — full breakdown скоринга, история похожих, прогноз α.
- Вкладка **«Ниша»** — n_eff, средний α, топ-поставщики, captive heatmap.

---

## 4. Roadmap изменений (привязано к стратегическому плану 3 месяцев)

### Спринт 1 (неделя 1–2). Фундамент.
- [ ] **Парсер протоколов** (`fetch_protocols.py`): по reg_number забирать страницу итогов, сохранять `final_price`, всех участников и победителя.
- [ ] **Миграция БД**: добавить `suppliers`, `lot_participations`, `lot_scores`, `price_benchmarks`, `niche_slug` на `lots`.
- [ ] **`niche_mapping.py`**: жёсткий справочник ОКПД2 → niche для 5–7 ваших целевых ниш.
- [ ] **Историческая загрузка**: догрузить минимум 30 000 лотов по выбранной нише за 12 месяцев (без этого скоринг бесполезен).

### Спринт 2 (неделя 3–4). Profit Score v1.
- [ ] **`benchmark.py`**: расчёт PriceBenchmark по нише+региону+12мес. Cron — раз в сутки.
- [ ] **`profit.py`** с реализацией всех 6 сигналов (margin, competition, captive, timing, spec_purity, customer_health). Веса — экспертные.
- [ ] **`rigged_detector.py`**: regex-детектор «заточки» (10–20 паттернов).
- [ ] **Cron-задача**: `daily_scoring.py` — каждое утро пересчитывать score для всех активных лотов.
- [ ] **Telegram-бот**: digest для 2–3 пилотных клиентов.

### Спринт 3 (неделя 5–8). Качество данных и продукт.
- [ ] Обогащение ИНН → DaData (выручка, статус, годы регистрации).
- [ ] Парсер РНП.
- [ ] Парсер жалоб ФАС.
- [ ] Дашборд: вкладка «Лоты под меня» + breakdown скоринга.
- [ ] Расширение БД до 5 регионов, 100k+ лотов.
- [ ] Калибровка весов скоринга на исторических данных (логит-регрессия).

### Спринт 4 (неделя 9–12). NLP и масштаб.
- [ ] Embeddings (`multilingual-e5-base`) для семантического поиска и кластеризации лотов.
- [ ] Извлечение единиц измерения из ТЗ (regex + NER) → удельная цена.
- [ ] PDF-парсинг полного ТЗ.
- [ ] FastAPI-слой → отделение дашборда от БД.
- [ ] Метрика «реалистичный winrate в нише» — ML-модель (gradient boosting), таргет = `is_winner` для конкретного supplier_id × niche × customer.

---

## 5. KPI аналитики (как мерить, что улучшилось)

| KPI | Текущее | Цель через 3 мес |
|---|---|---|
| Покрытие протоколов (`final_price` не NULL) | <5% | ≥80% (для лотов в статусе «Завершено») |
| Покрытие `participants_count` уникальными ИНН | 0% | ≥80% |
| Доля лотов с `niche_slug` | 0% | ≥95% |
| Доля лотов с `profit_score` | 0% | 100% активных |
| Среднее число лотов в digest клиента | — | 5–15 |
| Доля digest-лотов с реальной маржой ≥10% (по факту участия) | — | ≥60% (precision) |
| Recall: % выигранных клиентом лотов, попавших в его digest | — | ≥80% |
| Время от публикации лота на zakupki.gov.ru до digest клиенту | — | <2 ч |

**Главные две метрики:** **precision и recall дайджеста**. Всё остальное — приборная панель. Если из 10 лотов в утреннем digest клиент берёт 3 в работу и выигрывает 1 — система работает.

---

## 6. TL;DR

1. **Текущая аналитика — описательная статистика для дашборда, не движок прибыли.** Считает «сколько лотов» и «средняя цена», но не отвечает на вопрос «стоит ли мне участвовать в этом лоте».
2. **Главные 3 гэпа:** нет данных о поставщиках/победителях; нет price benchmark; нет агрегированного Profit Score.
3. **Минимальный набор изменений (4 недели):**
    - парсить протоколы итогов → есть победители и participants;
    - таблицы `suppliers`, `lot_participations`, `lot_scores`, `price_benchmarks`;
    - `niche_slug` через ОКПД2-маппинг;
    - Profit Score (margin, competition, captive, timing, spec_purity, customer_health);
    - Telegram-дайджест клиенту.
4. **Дальше (через 3 мес):** NLP-кластеризация, ML-калибровка весов, ИНН-обогащение, ФАС/РНП.
5. **KPI системы — precision/recall дайджеста**, а не количество вкладок в дашборде.
6. **Объём данных:** 150 лотов сейчас → надо минимум 50–100k лотов в нише за 12 месяцев. Без этого скоринг не работает.
