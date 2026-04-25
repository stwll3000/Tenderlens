"""
Модуль для анализа цен в госзакупках.

Функции:
- calculate_price_reduction: расчёт снижения цены (α)
- analyze_price_distribution: статистика распределения цен
- price_stats_by_region: анализ цен по регионам
- price_stats_by_law: анализ цен по законам (44-ФЗ vs 223-ФЗ)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple


def calculate_price_reduction(
    initial_price: float, 
    final_price: float
) -> float:
    """
    Расчёт снижения цены (α) в процентах.
    
    Формула: α = (НМЦ − цена победы) / НМЦ × 100%
    
    Args:
        initial_price: начальная максимальная цена (НМЦ)
        final_price: цена победителя
    
    Returns:
        Процент снижения цены
    
    Example:
        >>> calculate_price_reduction(1000000, 950000)
        5.0
    """
    if initial_price == 0:
        return 0.0
    
    reduction = ((initial_price - final_price) / initial_price) * 100
    return round(reduction, 2)


def analyze_price_distribution(df: pd.DataFrame) -> Dict:
    """
    Анализ распределения начальных цен.
    
    Args:
        df: DataFrame с данными о лотах
    
    Returns:
        Словарь со статистикой:
        - count: количество лотов
        - mean: средняя цена
        - median: медианная цена
        - std: стандартное отклонение
        - min/max: минимум/максимум
        - q25/q75: квартили
    """
    prices = df['initial_price'].dropna()
    
    stats = {
        'count': len(prices),
        'mean': prices.mean(),
        'median': prices.median(),
        'std': prices.std(),
        'min': prices.min(),
        'max': prices.max(),
        'q25': prices.quantile(0.25),
        'q75': prices.quantile(0.75),
        'total_volume': prices.sum()
    }
    
    return stats


def price_stats_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """
    Статистика цен по регионам.
    
    Args:
        df: DataFrame с данными о лотах
    
    Returns:
        DataFrame с агрегированной статистикой по регионам
    """
    stats = df.groupby('region_name')['initial_price'].agg([
        ('count', 'count'),
        ('mean', 'mean'),
        ('median', 'median'),
        ('total', 'sum'),
        ('min', 'min'),
        ('max', 'max')
    ]).round(2)
    
    stats = stats.sort_values('total', ascending=False)
    return stats


def price_stats_by_law(df: pd.DataFrame) -> pd.DataFrame:
    """
    Статистика цен по законам (44-ФЗ vs 223-ФЗ).
    
    Args:
        df: DataFrame с данными о лотах
    
    Returns:
        DataFrame с агрегированной статистикой по законам
    """
    stats = df.groupby('law')['initial_price'].agg([
        ('count', 'count'),
        ('mean', 'mean'),
        ('median', 'median'),
        ('total', 'sum'),
        ('min', 'min'),
        ('max', 'max')
    ]).round(2)
    
    return stats


def price_percentiles(df: pd.DataFrame, percentiles: list = [10, 25, 50, 75, 90]) -> Dict:
    """
    Расчёт перцентилей цен.
    
    Args:
        df: DataFrame с данными о лотах
        percentiles: список перцентилей для расчёта
    
    Returns:
        Словарь {перцентиль: значение}
    """
    prices = df['initial_price'].dropna()
    
    result = {}
    for p in percentiles:
        result[f'p{p}'] = prices.quantile(p / 100)
    
    return result


def identify_outliers(df: pd.DataFrame, method: str = 'iqr') -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Выявление выбросов в ценах.
    
    Args:
        df: DataFrame с данными о лотах
        method: метод выявления ('iqr' или 'zscore')
    
    Returns:
        Tuple (нормальные лоты, выбросы)
    """
    prices = df['initial_price']
    
    if method == 'iqr':
        q1 = prices.quantile(0.25)
        q3 = prices.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        mask = (prices >= lower_bound) & (prices <= upper_bound)
    
    elif method == 'zscore':
        z_scores = np.abs((prices - prices.mean()) / prices.std())
        mask = z_scores < 3
    
    else:
        raise ValueError(f"Unknown method: {method}")
    
    normal = df[mask]
    outliers = df[~mask]
    
    return normal, outliers


def price_summary(df: pd.DataFrame) -> str:
    """
    Текстовая сводка по ценам.
    
    Args:
        df: DataFrame с данными о лотах
    
    Returns:
        Форматированная строка со статистикой
    """
    stats = analyze_price_distribution(df)
    
    summary = f"""
=== АНАЛИЗ ЦЕН ===

Количество лотов: {stats['count']:,}
Общий объём: {stats['total_volume']:,.2f} руб.

Средняя цена: {stats['mean']:,.2f} руб.
Медианная цена: {stats['median']:,.2f} руб.
Стандартное отклонение: {stats['std']:,.2f} руб.

Минимум: {stats['min']:,.2f} руб.
25% квартиль: {stats['q25']:,.2f} руб.
75% квартиль: {stats['q75']:,.2f} руб.
Максимум: {stats['max']:,.2f} руб.
"""
    
    return summary
