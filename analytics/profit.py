"""
Модуль для расчёта Profit Score лота.

Profit Score — агрегированная метрика прибыльности лота для МСБ-поставщика.
Учитывает 6 компонентов:
- A. Margin signal: НМЦ выше медианы рынка
- B. Competition signal: низкая конкуренция
- C. Captive signal: заказчик не "captive"
- D. Timing signal: здоровые сроки подачи
- E. Spec purity signal: ТЗ без "заточки"
- F. Customer health: платёжеспособность заказчика
"""

from dataclasses import dataclass, field
import math
import json
import re
from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.models import Lot, LotParticipation, PriceBenchmark, Customer, LotScore
from analytics.benchmark import get_benchmark


@dataclass
class ProfitSignals:
    """Компоненты Profit Score."""
    margin: float = 0.0          # A: 0..1 (1 = НМЦ сильно выше медианы)
    competition: float = 0.0     # B: 0..1 (1 = низкая конкуренция)
    captive: float = 0.0         # C: 0..1 (1 = НЕ captive)
    timing: float = 0.0          # D: 0..1 (1 = здоровые сроки)
    spec_purity: float = 0.0     # E: 0..1 (1 = ТЗ чистое)
    customer_health: float = 0.0 # F: 0..1 (1 = заказчик здоров)
    flags: List[str] = field(default_factory=list)


# Веса компонентов (откалибровать на исторических данных)
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
def margin_signal(lot: Lot, benchmark: Optional[PriceBenchmark]) -> Tuple[float, List[str]]:
    """
    Сигнал маржинальности: насколько НМЦ выше медианы рынка.
    
    Args:
        lot: лот для оценки
        benchmark: benchmark по нише
    
    Returns:
        (score, flags) где score в [0, 1]
    """
    flags = []
    
    if not benchmark or not benchmark.median_initial_price:
        return 0.5, ["no_benchmark"]
    
    ratio = lot.initial_price / benchmark.median_initial_price
    
    # ratio=1.0 → 0.5; ratio=1.30 → ~0.95; ratio=0.7 → ~0.05
    score = _sigmoid((ratio - 1.0) * 5.0)
    
    if ratio > 1.20:
        flags.append("premium_nmc")
    if ratio < 0.80:
        flags.append("underpriced")
    
    return score, flags


# ---------- B. Competition signal ----------
def competition_signal(
    avg_unique_suppliers_in_niche: Optional[float],
    participants_count: Optional[int],
) -> Tuple[float, List[str]]:
    """
    Сигнал конкуренции: чем меньше участников, тем лучше.
    
    Args:
        avg_unique_suppliers_in_niche: среднее число поставщиков в нише
        participants_count: число участников в текущем лоте
    
    Returns:
        (score, flags) где score в [0, 1]
    """
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
def captive_signal(session: Session, customer_url: str, niche_slug: Optional[str]) -> Tuple[float, List[str]]:
    """
    Детектор "captive" заказчика: есть ли у него "свой" поставщик.
    
    Args:
        session: SQLAlchemy сессия
        customer_url: URL заказчика
        niche_slug: ниша лота
    
    Returns:
        (score, flags) где 1.0 = нет captive, 0.0 = есть captive
    """
    if not niche_slug:
        return 0.7, ["no_niche"]
    
    # Получаем историю побед поставщиков у этого заказчика в данной нише
    query = session.query(
        LotParticipation.supplier_id,
        func.count(LotParticipation.id).label('wins')
    ).join(
        Lot, Lot.id == LotParticipation.lot_id
    ).filter(
        LotParticipation.is_winner == True,
        Lot.customer_url == customer_url,
        Lot.niche_slug == niche_slug,
    ).group_by(
        LotParticipation.supplier_id
    ).order_by(
        func.count(LotParticipation.id).desc()
    ).limit(5).all()
    
    if not query:
        return 0.7, ["no_history"]
    
    total = sum(r.wins for r in query)
    top_share = query[0].wins / total if total else 0
    
    if top_share >= 0.8:
        return 0.05, ["captive_customer"]
    if top_share >= 0.6:
        return 0.30, ["likely_captive"]
    if top_share >= 0.4:
        return 0.60, []
    
    return 0.95, []


# ---------- D. Timing signal ----------
def timing_signal(deadline_days: Optional[int], law: str) -> Tuple[float, List[str]]:
    """
    Сигнал сроков: оптимум 7-14 дней для 44-ФЗ.
    
    Args:
        deadline_days: дней до дедлайна
        law: закон (44-ФЗ или 223-ФЗ)
    
    Returns:
        (score, flags)
    """
    if deadline_days is None:
        return 0.5, []
    
    if deadline_days < 3:
        return 0.20, ["rushed"]
    if deadline_days < 7:
        return 0.85, ["short_window_low_competition"]
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


def spec_purity_signal(object_name: str, tz_text: Optional[str]) -> Tuple[float, List[str]]:
    """
    Детектор "заточки" ТЗ под конкретного поставщика.
    
    Args:
        object_name: название объекта закупки
        tz_text: полный текст ТЗ
    
    Returns:
        (score, flags)
    """
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
def customer_health_signal(customer: Customer) -> Tuple[float, List[str]]:
    """
    Оценка платёжеспособности заказчика.
    
    Args:
        customer: объект заказчика
    
    Returns:
        (score, flags)
    """
    flags = []
    
    if customer.in_rnp:
        return 0.0, ["customer_in_rnp"]
    
    score = 0.5
    
    # +0.2 если есть исполненные контракты за 12 мес
    if (customer.completed_contracts_12m or 0) > 5:
        score += 0.2
    
    # +0.2 если средняя задержка платежа < 30 дней
    avg_delay = customer.avg_payment_delay_days
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
    customer: Customer,
) -> Tuple[float, ProfitSignals]:
    """
    Рассчитывает Profit Score для лота.
    
    Args:
        session: SQLAlchemy сессия
        lot: лот для оценки
        customer: заказчик лота
    
    Returns:
        (profit_score, signals) где profit_score в [0, 100]
    """
    sig = ProfitSignals()
    
    # Получаем benchmark
    benchmark = None
    if lot.niche_slug:
        benchmark = get_benchmark(session, lot.niche_slug, lot.region_code)
    
    # Рассчитываем компоненты
    sig.margin, f1 = margin_signal(lot, benchmark)
    
    avg_suppliers = benchmark.avg_unique_suppliers if benchmark else None
    sig.competition, f2 = competition_signal(avg_suppliers, lot.participants_count)
    
    sig.captive, f3 = captive_signal(session, lot.customer_url, lot.niche_slug)
    
    deadline_days = _deadline_days(lot)
    sig.timing, f4 = timing_signal(deadline_days, lot.law)
    
    sig.spec_purity, f5 = spec_purity_signal(lot.object_name, lot.tz_text)
    
    sig.customer_health, f6 = customer_health_signal(customer)
    
    sig.flags = f1 + f2 + f3 + f4 + f5 + f6
    
    # Агрегируем score
    score = sum(getattr(sig, k) * w for k, w in WEIGHTS.items()) * 100
    
    # Hard veto: customer in РНП — score 0
    if "customer_in_rnp" in sig.flags:
        score = 0
    
    return round(score, 1), sig


def _deadline_days(lot: Lot) -> Optional[int]:
    """Рассчитывает количество дней до дедлайна."""
    try:
        pub = datetime.strptime(lot.published_date, "%d.%m.%Y")
        dead = datetime.strptime(lot.deadline_date, "%d.%m.%Y")
        d = (dead - pub).days
        return d if d >= 0 else None
    except (ValueError, TypeError, AttributeError):
        return None


def save_lot_score(
    session: Session,
    lot: Lot,
    profit_score: float,
    signals: ProfitSignals
) -> LotScore:
    """
    Сохраняет результат скоринга в БД.
    
    Args:
        session: SQLAlchemy сессия
        lot: лот
        profit_score: итоговый score
        signals: компоненты score
    
    Returns:
        LotScore объект
    """
    # Проверяем, есть ли уже score для этого лота
    existing = session.query(LotScore).filter_by(lot_id=lot.id).first()
    
    if existing:
        # Обновляем существующий
        existing.profit_score = profit_score
        existing.margin_signal = signals.margin
        existing.competition_signal = signals.competition
        existing.captive_signal = signals.captive
        existing.timing_signal = signals.timing
        existing.spec_purity_signal = signals.spec_purity
        existing.customer_health = signals.customer_health
        existing.flags_json = json.dumps(signals.flags, ensure_ascii=False)
        existing.computed_at = datetime.now()
        lot_score = existing
    else:
        # Создаём новый
        lot_score = LotScore(
            lot_id=lot.id,
            profit_score=profit_score,
            margin_signal=signals.margin,
            competition_signal=signals.competition,
            captive_signal=signals.captive,
            timing_signal=signals.timing,
            spec_purity_signal=signals.spec_purity,
            customer_health=signals.customer_health,
            flags_json=json.dumps(signals.flags, ensure_ascii=False),
        )
        session.add(lot_score)
    
    session.commit()
    return lot_score


def score_all_lots(session: Session, batch_size: int = 100) -> dict:
    """
    Рассчитывает Profit Score для всех активных лотов.
    
    Args:
        session: SQLAlchemy сессия
        batch_size: размер батча
    
    Returns:
        Статистика: {'scored': int, 'failed': int}
    """
    import logging
    logger = logging.getLogger(__name__)
    
    stats = {'scored': 0, 'failed': 0}
    
    # Получаем активные лоты (статус "Подача заявок")
    lots = session.query(Lot).filter(
        Lot.status.in_(["Подача заявок", "Работа комиссии"])
    ).all()
    
    logger.info(f"Начинаем скоринг {len(lots)} лотов")
    
    for lot in lots:
        try:
            # Получаем заказчика
            customer = session.query(Customer).filter_by(url=lot.customer_url).first()
            
            if not customer:
                logger.warning(f"Заказчик не найден для лота {lot.reg_number}")
                stats['failed'] += 1
                continue
            
            # Рассчитываем score
            profit_score, signals = compute_profit_score(session, lot, customer)
            
            # Сохраняем
            save_lot_score(session, lot, profit_score, signals)
            
            stats['scored'] += 1
            
            if stats['scored'] % 100 == 0:
                logger.info(f"Обработано {stats['scored']} лотов")
                
        except Exception as e:
            logger.error(f"Ошибка при скоринге лота {lot.reg_number}: {e}")
            stats['failed'] += 1
    
    logger.info(f"Скоринг завершён: scored={stats['scored']}, failed={stats['failed']}")
    
    return stats


if __name__ == "__main__":
    # Тестирование
    from db.connection import get_session
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    with get_session() as session:
        # Получаем первый лот для теста
        lot = session.query(Lot).first()
        
        if lot:
            customer = session.query(Customer).filter_by(url=lot.customer_url).first()
            
            if customer:
                score, signals = compute_profit_score(session, lot, customer)
                
                print(f"\nProfit Score для лота {lot.reg_number}:")
                print(f"  Итоговый score: {score:.1f}/100")
                print(f"  Компоненты:")
                print(f"    Margin:          {signals.margin:.2f}")
                print(f"    Competition:     {signals.competition:.2f}")
                print(f"    Captive:         {signals.captive:.2f}")
                print(f"    Timing:          {signals.timing:.2f}")
                print(f"    Spec purity:     {signals.spec_purity:.2f}")
                print(f"    Customer health: {signals.customer_health:.2f}")
                print(f"  Флаги: {', '.join(signals.flags) if signals.flags else 'нет'}")
