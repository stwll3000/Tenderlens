"""
Модуль для расчёта price benchmark по нише/региону/периоду.

Функции:
- compute_niche_benchmark: расчёт benchmark для конкретной ниши
- get_benchmark: получение актуального benchmark из БД
- compute_all_benchmarks: пересчёт всех benchmark'ов
"""

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date, timedelta, datetime
from typing import Optional, List
import logging

from db.models import Lot, PriceBenchmark, LotParticipation

logger = logging.getLogger(__name__)


def compute_niche_benchmark(
    session: Session,
    niche_slug: str,
    region_code: Optional[str] = None,
    months: int = 12,
) -> Optional[PriceBenchmark]:
    """
    Рассчитывает price benchmark для конкретной ниши.
    
    Args:
        session: SQLAlchemy сессия
        niche_slug: идентификатор ниши
        region_code: код региона (опционально, None = все регионы)
        months: период для расчёта (по умолчанию 12 месяцев)
    
    Returns:
        PriceBenchmark объект или None, если недостаточно данных
    """
    today = date.today()
    start_date = today - timedelta(days=30 * months)
    
    # Строим запрос для получения лотов
    query = session.query(Lot).filter(
        Lot.niche_slug == niche_slug,
        Lot.scraped_at >= datetime.combine(start_date, datetime.min.time()),
    )
    
    if region_code:
        query = query.filter(Lot.region_code == region_code)
    
    # Получаем данные
    lots = query.all()
    
    if len(lots) < 30:
        logger.warning(
            f"Недостаточно данных для benchmark: niche={niche_slug}, "
            f"region={region_code}, lots={len(lots)} (минимум 30)"
        )
        return None
    
    # Конвертируем в DataFrame для удобства расчётов
    data = []
    for lot in lots:
        data.append({
            'initial_price': lot.initial_price,
            'final_price': lot.final_price,
            'price_reduction_pct': lot.price_reduction_pct,
        })
    
    df = pd.DataFrame(data)
    
    # Рассчитываем медианы
    median_initial = float(df['initial_price'].median())
    
    # Для final_price и alpha нужно минимум 10 значений
    median_final = None
    median_alpha = None
    
    if df['final_price'].notna().sum() >= 10:
        median_final = float(df['final_price'].median())
    
    if df['price_reduction_pct'].notna().sum() >= 10:
        median_alpha = float(df['price_reduction_pct'].median())
    
    # Рассчитываем среднее количество уникальных поставщиков
    avg_suppliers = _calculate_avg_suppliers(session, niche_slug, region_code, start_date)
    
    # Создаём или обновляем benchmark
    existing = session.query(PriceBenchmark).filter(
        PriceBenchmark.niche_slug == niche_slug,
        PriceBenchmark.region_code == region_code,
    ).order_by(PriceBenchmark.computed_at.desc()).first()
    
    if existing and (datetime.now() - existing.computed_at).days < 1:
        # Обновляем существующий, если он свежий (менее суток)
        existing.period_start = start_date
        existing.period_end = today
        existing.sample_size = len(lots)
        existing.median_initial_price = median_initial
        existing.median_final_price = median_final
        existing.median_alpha = median_alpha
        existing.avg_unique_suppliers = avg_suppliers
        existing.computed_at = datetime.now()
        benchmark = existing
    else:
        # Создаём новый
        benchmark = PriceBenchmark(
            niche_slug=niche_slug,
            region_code=region_code,
            period_start=start_date,
            period_end=today,
            sample_size=len(lots),
            median_initial_price=median_initial,
            median_final_price=median_final,
            median_alpha=median_alpha,
            avg_unique_suppliers=avg_suppliers,
        )
        session.add(benchmark)
    
    session.commit()
    
    logger.info(
        f"Benchmark рассчитан: niche={niche_slug}, region={region_code}, "
        f"sample={len(lots)}, median_price={median_initial:.2f}"
    )
    
    return benchmark


def _calculate_avg_suppliers(
    session: Session,
    niche_slug: str,
    region_code: Optional[str],
    start_date: date
) -> Optional[float]:
    """
    Рассчитывает среднее количество уникальных поставщиков на лот в нише.
    
    Args:
        session: SQLAlchemy сессия
        niche_slug: идентификатор ниши
        region_code: код региона
        start_date: начальная дата периода
    
    Returns:
        Среднее количество поставщиков или None
    """
    # Подзапрос: количество участников на каждый лот
    subquery = session.query(
        LotParticipation.lot_id,
        func.count(func.distinct(LotParticipation.supplier_id)).label('suppliers_count')
    ).join(
        Lot, Lot.id == LotParticipation.lot_id
    ).filter(
        Lot.niche_slug == niche_slug,
        Lot.scraped_at >= datetime.combine(start_date, datetime.min.time()),
    )
    
    if region_code:
        subquery = subquery.filter(Lot.region_code == region_code)
    
    subquery = subquery.group_by(LotParticipation.lot_id).subquery()
    
    # Средняя по всем лотам
    result = session.query(func.avg(subquery.c.suppliers_count)).scalar()
    
    return float(result) if result else None


def get_benchmark(
    session: Session,
    niche_slug: str,
    region_code: Optional[str] = None,
    max_age_days: int = 7
) -> Optional[PriceBenchmark]:
    """
    Получает актуальный benchmark из БД.
    
    Args:
        session: SQLAlchemy сессия
        niche_slug: идентификатор ниши
        region_code: код региона
        max_age_days: максимальный возраст benchmark в днях
    
    Returns:
        PriceBenchmark или None
    """
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    
    benchmark = session.query(PriceBenchmark).filter(
        PriceBenchmark.niche_slug == niche_slug,
        PriceBenchmark.region_code == region_code,
        PriceBenchmark.computed_at >= cutoff_date
    ).order_by(PriceBenchmark.computed_at.desc()).first()
    
    return benchmark


def compute_all_benchmarks(
    session: Session,
    months: int = 12,
    force_recompute: bool = False
) -> dict:
    """
    Пересчитывает benchmark'ы для всех ниш и регионов.
    
    Args:
        session: SQLAlchemy сессия
        months: период для расчёта
        force_recompute: пересчитывать даже свежие benchmark'ы
    
    Returns:
        Словарь со статистикой: {'computed': int, 'skipped': int, 'failed': int}
    """
    from features.niche_mapping import NICHE_MAP
    
    stats = {'computed': 0, 'skipped': 0, 'failed': 0}
    
    # Получаем список уникальных регионов из БД
    regions = session.query(Lot.region_code).distinct().all()
    region_codes = [r[0] for r in regions if r[0]]
    
    # Добавляем None для общего benchmark (все регионы)
    region_codes.append(None)
    
    logger.info(f"Начинаем расчёт benchmark'ов для {len(NICHE_MAP)} ниш и {len(region_codes)} регионов")
    
    for niche_slug in NICHE_MAP.keys():
        for region_code in region_codes:
            # Проверяем, нужно ли пересчитывать
            if not force_recompute:
                existing = get_benchmark(session, niche_slug, region_code, max_age_days=1)
                if existing:
                    logger.debug(f"Пропускаем свежий benchmark: {niche_slug}/{region_code}")
                    stats['skipped'] += 1
                    continue
            
            try:
                benchmark = compute_niche_benchmark(
                    session,
                    niche_slug,
                    region_code,
                    months
                )
                
                if benchmark:
                    stats['computed'] += 1
                else:
                    stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Ошибка при расчёте benchmark {niche_slug}/{region_code}: {e}")
                stats['failed'] += 1
    
    logger.info(
        f"Расчёт benchmark'ов завершён: "
        f"computed={stats['computed']}, skipped={stats['skipped']}, failed={stats['failed']}"
    )
    
    return stats


if __name__ == "__main__":
    # Тестирование
    from db.connection import get_session
    
    logging.basicConfig(level=logging.INFO)
    
    with get_session() as session:
        # Пример: расчёт benchmark для медицинских расходников в Москве
        benchmark = compute_niche_benchmark(
            session,
            niche_slug="med-rashodniki",
            region_code="77",
            months=12
        )
        
        if benchmark:
            print(f"Benchmark рассчитан:")
            print(f"  Ниша: {benchmark.niche_slug}")
            print(f"  Регион: {benchmark.region_code}")
            print(f"  Выборка: {benchmark.sample_size} лотов")
            print(f"  Медианная НМЦ: {benchmark.median_initial_price:,.2f} ₽")
            print(f"  Медианная цена победы: {benchmark.median_final_price:,.2f} ₽" if benchmark.median_final_price else "  Медианная цена победы: N/A")
            print(f"  Медианное снижение: {benchmark.median_alpha:.2f}%" if benchmark.median_alpha else "  Медианное снижение: N/A")
            print(f"  Среднее число поставщиков: {benchmark.avg_unique_suppliers:.1f}" if benchmark.avg_unique_suppliers else "  Среднее число поставщиков: N/A")
