"""
Модуль для анализа конкуренции в госзакупках.

Функции:
- analyze_by_region: анализ по регионам
- analyze_by_law: сравнение 44-ФЗ vs 223-ФЗ
- top_customers: топ заказчиков
- market_concentration: концентрация рынка (индекс Херфиндаля)
- customer_activity: активность заказчиков
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


def analyze_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """
    Анализ закупок по регионам.
    
    Args:
        df: DataFrame с данными о лотах
    
    Returns:
        DataFrame с метриками по регионам
    """
    stats = df.groupby('region_name').agg({
        'reg_number': 'count',
        'initial_price': ['sum', 'mean', 'median'],
        'customer_name': 'nunique'
    }).round(2)
    
    stats.columns = ['lots_count', 'total_volume', 'avg_price', 'median_price', 'unique_customers']
    stats = stats.sort_values('total_volume', ascending=False)
    
    return stats


def analyze_by_law(df: pd.DataFrame) -> pd.DataFrame:
    """
    Сравнение закупок по законам (44-ФЗ vs 223-ФЗ).
    
    Args:
        df: DataFrame с данными о лотах
    
    Returns:
        DataFrame с метриками по законам
    """
    stats = df.groupby('law').agg({
        'reg_number': 'count',
        'initial_price': ['sum', 'mean', 'median'],
        'customer_name': 'nunique'
    }).round(2)
    
    stats.columns = ['lots_count', 'total_volume', 'avg_price', 'median_price', 'unique_customers']
    
    # Добавляем процентное соотношение
    stats['lots_pct'] = (stats['lots_count'] / stats['lots_count'].sum() * 100).round(2)
    stats['volume_pct'] = (stats['total_volume'] / stats['total_volume'].sum() * 100).round(2)
    
    return stats


def top_customers(df: pd.DataFrame, n: int = 10, by: str = 'count') -> pd.DataFrame:
    """
    Топ заказчиков по количеству или объёму закупок.
    
    Args:
        df: DataFrame с данными о лотах
        n: количество топ заказчиков
        by: критерий сортировки ('count' или 'volume')
    
    Returns:
        DataFrame с топ заказчиками
    """
    stats = df.groupby('customer_name').agg({
        'reg_number': 'count',
        'initial_price': 'sum'
    }).round(2)
    
    stats.columns = ['lots_count', 'total_volume']
    
    if by == 'count':
        stats = stats.sort_values('lots_count', ascending=False)
    elif by == 'volume':
        stats = stats.sort_values('total_volume', ascending=False)
    else:
        raise ValueError(f"Unknown sorting criterion: {by}")
    
    return stats.head(n)


def market_concentration(df: pd.DataFrame, by: str = 'volume') -> Dict:
    """
    Расчёт концентрации рынка (индекс Херфиндаля-Хиршмана).
    
    HHI = Σ(market_share_i)²
    
    Args:
        df: DataFrame с данными о лотах
        by: критерий ('volume' или 'count')
    
    Returns:
        Словарь с метриками концентрации
    """
    if by == 'volume':
        customer_stats = df.groupby('customer_name')['initial_price'].sum()
        total = customer_stats.sum()
    elif by == 'count':
        customer_stats = df.groupby('customer_name').size()
        total = customer_stats.sum()
    else:
        raise ValueError(f"Unknown criterion: {by}")
    
    # Доли рынка в процентах
    market_shares = (customer_stats / total * 100)
    
    # Индекс Херфиндаля-Хиршмана
    hhi = (market_shares ** 2).sum()
    
    # Топ-3, топ-5, топ-10
    top3_share = market_shares.nlargest(3).sum()
    top5_share = market_shares.nlargest(5).sum()
    top10_share = market_shares.nlargest(10).sum()
    
    return {
        'hhi': round(hhi, 2),
        'top3_share': round(top3_share, 2),
        'top5_share': round(top5_share, 2),
        'top10_share': round(top10_share, 2),
        'total_customers': len(customer_stats),
        'interpretation': interpret_hhi(hhi)
    }


def interpret_hhi(hhi: float) -> str:
    """
    Интерпретация индекса Херфиндаля-Хиршмана.
    
    Args:
        hhi: значение индекса
    
    Returns:
        Текстовая интерпретация
    """
    if hhi < 1000:
        return "Низкая концентрация (конкурентный рынок)"
    elif hhi < 1800:
        return "Умеренная концентрация"
    else:
        return "Высокая концентрация (олигополия)"


def customer_activity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Анализ активности заказчиков.
    
    Args:
        df: DataFrame с данными о лотах
    
    Returns:
        DataFrame с метриками активности
    """
    stats = df.groupby('customer_name').agg({
        'reg_number': 'count',
        'initial_price': ['sum', 'mean', 'min', 'max'],
        'law': lambda x: (x == '44-ФЗ').sum() / len(x) * 100
    }).round(2)
    
    stats.columns = ['lots_count', 'total_volume', 'avg_price', 'min_price', 'max_price', 'fz44_pct']
    stats = stats.sort_values('lots_count', ascending=False)
    
    return stats


def analyze_by_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    Анализ закупок по статусам.
    
    Args:
        df: DataFrame с данными о лотах
    
    Returns:
        DataFrame с метриками по статусам
    """
    stats = df.groupby('status').agg({
        'reg_number': 'count',
        'initial_price': ['sum', 'mean']
    }).round(2)
    
    stats.columns = ['lots_count', 'total_volume', 'avg_price']
    stats['lots_pct'] = (stats['lots_count'] / stats['lots_count'].sum() * 100).round(2)
    stats = stats.sort_values('lots_count', ascending=False)
    
    return stats


def analyze_by_purchase_method(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Анализ по способам определения поставщика.
    
    Args:
        df: DataFrame с данными о лотах
        top_n: количество топ методов
    
    Returns:
        DataFrame с метриками по методам
    """
    stats = df.groupby('purchase_method').agg({
        'reg_number': 'count',
        'initial_price': ['sum', 'mean']
    }).round(2)
    
    stats.columns = ['lots_count', 'total_volume', 'avg_price']
    stats['lots_pct'] = (stats['lots_count'] / stats['lots_count'].sum() * 100).round(2)
    stats = stats.sort_values('lots_count', ascending=False)
    
    return stats.head(top_n)


def competition_summary(df: pd.DataFrame) -> str:
    """
    Текстовая сводка по конкуренции.
    
    Args:
        df: DataFrame с данными о лотах
    
    Returns:
        Форматированная строка со статистикой
    """
    concentration = market_concentration(df, by='volume')
    top3 = top_customers(df, n=3, by='volume')
    
    summary = f"""
=== АНАЛИЗ КОНКУРЕНЦИИ ===

Всего заказчиков: {concentration['total_customers']}

Концентрация рынка (HHI): {concentration['hhi']}
Интерпретация: {concentration['interpretation']}

Доля топ-3 заказчиков: {concentration['top3_share']}%
Доля топ-5 заказчиков: {concentration['top5_share']}%
Доля топ-10 заказчиков: {concentration['top10_share']}%

ТОП-3 ЗАКАЗЧИКА ПО ОБЪЁМУ:
"""
    
    for i, (name, row) in enumerate(top3.iterrows(), 1):
        summary += f"\n{i}. {name[:60]}..."
        summary += f"\n   Лотов: {row['lots_count']}, Объём: {row['total_volume']:,.2f} руб.\n"
    
    return summary
