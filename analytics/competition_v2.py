"""
Модуль для анализа конкуренции по поставщикам (v2).

В отличие от старого competition.py, который считал HHI по заказчикам,
этот модуль анализирует концентрацию ПОСТАВЩИКОВ в нише — что важно
для МСБ-поставщика, который ищет "куда вписаться".

Функции:
- supplier_concentration_in_niche: HHI и n_eff по поставщикам
- top_suppliers_in_niche: топ поставщиков в нише
- supplier_winrate: winrate конкретного поставщика
- niche_attractiveness: общая оценка привлекательности ниши
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

from db.models import Lot, LotParticipation, Supplier

logger = logging.getLogger(__name__)


def supplier_concentration_in_niche(
    session: Session,
    niche_slug: str,
    region_code: Optional[str] = None,
    months: int = 12
) -> Dict:
    """
    Рассчитывает концентрацию поставщиков в нише (HHI и n_eff).
    
    HHI (Herfindahl-Hirschman Index) — индекс концентрации рынка.
    n_eff — эффективное число игроков (1 / Σ(s_i²)).
    
    Args:
        session: SQLAlchemy сессия
        niche_slug: идентификатор ниши
        region_code: код региона (опционально)
        months: период анализа в месяцах
    
    Returns:
        Словарь с метриками:
        - hhi: индекс Херфиндаля (0..10000)
        - n_eff: эффективное число игроков
        - top1_share_pct: доля топ-1 поставщика (%)
        - total_suppliers: общее число поставщиков
        - total_wins: общее число побед
        - interpretation: текстовая интерпретация
    """
    cutoff_date = datetime.now() - timedelta(days=30 * months)
    
    # Получаем победы поставщиков в нише
    query = session.query(
        Supplier.inn,
        Supplier.name,
        func.count(LotParticipation.id).label('wins')
    ).join(
        LotParticipation, LotParticipation.supplier_id == Supplier.id
    ).join(
        Lot, Lot.id == LotParticipation.lot_id
    ).filter(
        LotParticipation.is_winner == True,
        Lot.niche_slug == niche_slug,
        Lot.scraped_at >= cutoff_date,
    )
    
    if region_code:
        query = query.filter(Lot.region_code == region_code)
    
    query = query.group_by(Supplier.inn, Supplier.name).all()
    
    if not query:
        return {
            "hhi": 0,
            "n_eff": 0,
            "top1_share_pct": 0,
            "total_suppliers": 0,
            "total_wins": 0,
            "interpretation": "Нет данных",
        }
    
    # Рассчитываем метрики
    total_wins = sum(r.wins for r in query)
    shares = [(r.inn, r.name, r.wins / total_wins) for r in query]
    
    # HHI = Σ(s_i * 100)²
    hhi = sum((s * 100) ** 2 for _, _, s in shares)
    
    # n_eff = 1 / Σ(s_i²)
    n_eff = 1 / sum(s ** 2 for _, _, s in shares) if shares else 0
    
    # Доля топ-1
    top1_share = max((s for _, _, s in shares), default=0) * 100
    
    interpretation = _interpret_concentration(hhi, n_eff)
    
    return {
        "hhi": round(hhi, 1),
        "n_eff": round(n_eff, 2),
        "top1_share_pct": round(top1_share, 1),
        "total_suppliers": len(shares),
        "total_wins": total_wins,
        "interpretation": interpretation,
        "top_suppliers": [
            {"inn": inn, "name": name, "share_pct": round(s * 100, 1)}
            for inn, name, s in sorted(shares, key=lambda x: x[2], reverse=True)[:5]
        ]
    }


def _interpret_concentration(hhi: float, n_eff: float) -> str:
    """Интерпретация концентрации рынка."""
    if n_eff < 2:
        return "Монополия — не лезть"
    if n_eff < 4:
        return "Олигополия — высокий риск 'своих'"
    if n_eff < 10:
        return "Здоровая ниша для МСБ"
    return "Раздробленная — низкая маржа из-за демпинга"


def top_suppliers_in_niche(
    session: Session,
    niche_slug: str,
    region_code: Optional[str] = None,
    months: int = 12,
    limit: int = 10
) -> List[Dict]:
    """
    Возвращает топ поставщиков в нише по числу побед.
    
    Args:
        session: SQLAlchemy сессия
        niche_slug: идентификатор ниши
        region_code: код региона
        months: период анализа
        limit: количество поставщиков
    
    Returns:
        Список словарей с данными о поставщиках
    """
    cutoff_date = datetime.now() - timedelta(days=30 * months)
    
    query = session.query(
        Supplier.inn,
        Supplier.name,
        Supplier.is_smp,
        func.count(LotParticipation.id).label('wins'),
        func.sum(Lot.initial_price).label('total_volume'),
        func.avg(Lot.initial_price).label('avg_lot_price'),
    ).join(
        LotParticipation, LotParticipation.supplier_id == Supplier.id
    ).join(
        Lot, Lot.id == LotParticipation.lot_id
    ).filter(
        LotParticipation.is_winner == True,
        Lot.niche_slug == niche_slug,
        Lot.scraped_at >= cutoff_date,
    )
    
    if region_code:
        query = query.filter(Lot.region_code == region_code)
    
    query = query.group_by(
        Supplier.inn, Supplier.name, Supplier.is_smp
    ).order_by(
        func.count(LotParticipation.id).desc()
    ).limit(limit)
    
    results = query.all()
    
    return [
        {
            "inn": r.inn,
            "name": r.name,
            "is_smp": r.is_smp,
            "wins": r.wins,
            "total_volume": float(r.total_volume) if r.total_volume else 0,
            "avg_lot_price": float(r.avg_lot_price) if r.avg_lot_price else 0,
        }
        for r in results
    ]


def supplier_winrate(
    session: Session,
    supplier_inn: str,
    niche_slug: Optional[str] = None,
    months: int = 12
) -> Dict:
    """
    Рассчитывает winrate конкретного поставщика.
    
    Args:
        session: SQLAlchemy сессия
        supplier_inn: ИНН поставщика
        niche_slug: ниша (опционально)
        months: период анализа
    
    Returns:
        Словарь с метриками winrate
    """
    cutoff_date = datetime.now() - timedelta(days=30 * months)
    
    supplier = session.query(Supplier).filter_by(inn=supplier_inn).first()
    
    if not supplier:
        return {"error": "Поставщик не найден"}
    
    # Общее число участий
    query_total = session.query(func.count(LotParticipation.id)).join(
        Lot, Lot.id == LotParticipation.lot_id
    ).filter(
        LotParticipation.supplier_id == supplier.id,
        Lot.scraped_at >= cutoff_date,
    )
    
    if niche_slug:
        query_total = query_total.filter(Lot.niche_slug == niche_slug)
    
    total_participations = query_total.scalar() or 0
    
    # Число побед
    query_wins = session.query(func.count(LotParticipation.id)).join(
        Lot, Lot.id == LotParticipation.lot_id
    ).filter(
        LotParticipation.supplier_id == supplier.id,
        LotParticipation.is_winner == True,
        Lot.scraped_at >= cutoff_date,
    )
    
    if niche_slug:
        query_wins = query_wins.filter(Lot.niche_slug == niche_slug)
    
    wins = query_wins.scalar() or 0
    
    winrate = (wins / total_participations * 100) if total_participations > 0 else 0
    
    return {
        "supplier_inn": supplier_inn,
        "supplier_name": supplier.name,
        "niche_slug": niche_slug,
        "total_participations": total_participations,
        "wins": wins,
        "winrate_pct": round(winrate, 1),
    }


def niche_attractiveness(
    session: Session,
    niche_slug: str,
    region_code: Optional[str] = None,
    months: int = 12
) -> Dict:
    """
    Общая оценка привлекательности ниши для МСБ-поставщика.
    
    Учитывает:
    - Концентрацию поставщиков (n_eff)
    - Объём рынка
    - Среднюю маржу (если есть данные)
    - Количество активных лотов
    
    Args:
        session: SQLAlchemy сессия
        niche_slug: идентификатор ниши
        region_code: код региона
        months: период анализа
    
    Returns:
        Словарь с оценкой привлекательности
    """
    cutoff_date = datetime.now() - timedelta(days=30 * months)
    
    # Концентрация
    concentration = supplier_concentration_in_niche(session, niche_slug, region_code, months)
    
    # Объём и количество лотов
    query = session.query(
        func.count(Lot.id).label('total_lots'),
        func.sum(Lot.initial_price).label('total_volume'),
        func.avg(Lot.initial_price).label('avg_price'),
        func.avg(Lot.price_reduction_pct).label('avg_margin'),
    ).filter(
        Lot.niche_slug == niche_slug,
        Lot.scraped_at >= cutoff_date,
    )
    
    if region_code:
        query = query.filter(Lot.region_code == region_code)
    
    result = query.first()
    
    # Оценка привлекательности (0-100)
    score = 50  # базовая оценка
    
    # +30 за здоровую конкуренцию (n_eff 4-10)
    if 4 <= concentration['n_eff'] < 10:
        score += 30
    elif concentration['n_eff'] >= 10:
        score += 10
    elif concentration['n_eff'] < 2:
        score -= 30
    
    # +10 за большой объём рынка
    if result.total_volume and result.total_volume > 100_000_000:
        score += 10
    
    # +10 за хорошую маржу
    if result.avg_margin and result.avg_margin > 5:
        score += 10
    
    score = max(0, min(100, score))
    
    return {
        "niche_slug": niche_slug,
        "region_code": region_code,
        "attractiveness_score": score,
        "n_eff": concentration['n_eff'],
        "interpretation": concentration['interpretation'],
        "total_lots": result.total_lots or 0,
        "total_volume": float(result.total_volume) if result.total_volume else 0,
        "avg_price": float(result.avg_price) if result.avg_price else 0,
        "avg_margin_pct": float(result.avg_margin) if result.avg_margin else None,
        "top_suppliers": concentration['top_suppliers'][:3],
    }


if __name__ == "__main__":
    # Тестирование
    from db.connection import get_session
    
    logging.basicConfig(level=logging.INFO)
    
    with get_session() as session:
        # Пример: анализ конкуренции в медицинских расходниках
        result = supplier_concentration_in_niche(
            session,
            niche_slug="med-rashodniki",
            region_code="77",
            months=12
        )
        
        print("\nКонцентрация поставщиков в нише 'med-rashodniki' (Москва):")
        print(f"  HHI: {result['hhi']}")
        print(f"  Эффективное число игроков: {result['n_eff']}")
        print(f"  Доля топ-1: {result['top1_share_pct']}%")
        print(f"  Всего поставщиков: {result['total_suppliers']}")
        print(f"  Интерпретация: {result['interpretation']}")
        
        if result['top_suppliers']:
            print("\n  Топ-3 поставщика:")
            for s in result['top_suppliers'][:3]:
                print(f"    {s['name']}: {s['share_pct']}%")
