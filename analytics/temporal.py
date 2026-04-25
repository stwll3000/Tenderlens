"""
Модуль временного анализа закупок.

Анализирует временные паттерны:
- Распределение по датам размещения
- Сроки подачи заявок
- Сезонность
- Дни недели
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Парсинг даты из строки DD.MM.YYYY"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%d.%m.%Y')
    except:
        return None


def calculate_deadline_days(df: pd.DataFrame) -> pd.Series:
    """
    Расчёт количества дней до дедлайна.
    
    Args:
        df: DataFrame с колонками published_date и deadline_date
        
    Returns:
        Series с количеством дней
    """
    published = pd.to_datetime(df['published_date'], format='%d.%m.%Y', errors='coerce')
    deadline = pd.to_datetime(df['deadline_date'], format='%d.%m.%Y', errors='coerce')
    
    days = (deadline - published).dt.days
    return days.where(days >= 0)  # Только положительные значения


def analyze_deadline_distribution(df: pd.DataFrame) -> Dict:
    """
    Анализ распределения сроков подачи заявок.
    
    Returns:
        Словарь со статистикой
    """
    days = calculate_deadline_days(df)
    valid_days = days.dropna()
    
    if len(valid_days) == 0:
        return {}
    
    # Распределение по диапазонам
    ranges = [
        (0, 3, 'Срочные (0-3 дня)'),
        (4, 7, 'Короткие (4-7 дней)'),
        (8, 14, 'Стандартные (8-14 дней)'),
        (15, 30, 'Длинные (15-30 дней)'),
        (31, 999, 'Очень длинные (>30 дней)')
    ]
    
    distribution = {}
    for start, end, label in ranges:
        count = ((valid_days >= start) & (valid_days <= end)).sum()
        distribution[label] = {
            'count': int(count),
            'percentage': float(count / len(valid_days) * 100)
        }
    
    return {
        'mean': float(valid_days.mean()),
        'median': float(valid_days.median()),
        'min': int(valid_days.min()),
        'max': int(valid_days.max()),
        'std': float(valid_days.std()),
        'distribution': distribution,
        'total_analyzed': len(valid_days)
    }


def analyze_publication_dates(df: pd.DataFrame) -> Dict:
    """
    Анализ дат размещения закупок.
    
    Returns:
        Словарь со статистикой
    """
    df = df.copy()
    df['pub_date'] = pd.to_datetime(df['published_date'], format='%d.%m.%Y', errors='coerce')
    df = df.dropna(subset=['pub_date'])
    
    if len(df) == 0:
        return {}
    
    # Общая статистика
    min_date = df['pub_date'].min()
    max_date = df['pub_date'].max()
    date_range = (max_date - min_date).days
    
    # По дням недели
    df['weekday'] = df['pub_date'].dt.day_name()
    weekday_counts = df['weekday'].value_counts().to_dict()
    
    # По месяцам
    df['month'] = df['pub_date'].dt.to_period('M')
    monthly_counts = df.groupby('month').size().to_dict()
    monthly_counts = {str(k): int(v) for k, v in monthly_counts.items()}
    
    # По неделям
    df['week'] = df['pub_date'].dt.to_period('W')
    weekly_counts = df.groupby('week').size().to_dict()
    weekly_counts = {str(k): int(v) for k, v in weekly_counts.items()}
    
    return {
        'date_range': {
            'start': min_date.strftime('%Y-%m-%d'),
            'end': max_date.strftime('%Y-%m-%d'),
            'days': date_range
        },
        'total_lots': len(df),
        'avg_per_day': float(len(df) / max(date_range, 1)),
        'by_weekday': weekday_counts,
        'by_month': monthly_counts,
        'by_week': weekly_counts
    }


def analyze_temporal_patterns(df: pd.DataFrame) -> Dict:
    """
    Комплексный временной анализ.
    
    Args:
        df: DataFrame с данными о закупках
        
    Returns:
        Словарь с результатами анализа
    """
    logger.info("Запуск временного анализа...")
    
    results = {
        'deadline_analysis': analyze_deadline_distribution(df),
        'publication_analysis': analyze_publication_dates(df),
    }
    
    # Анализ по законам
    if 'law' in df.columns:
        results['by_law'] = {}
        for law in df['law'].unique():
            law_df = df[df['law'] == law]
            results['by_law'][law] = {
                'deadline': analyze_deadline_distribution(law_df),
                'publication': analyze_publication_dates(law_df)
            }
    
    logger.info("Временной анализ завершён")
    return results


def get_upcoming_deadlines(df: pd.DataFrame, days_ahead: int = 7) -> pd.DataFrame:
    """
    Получить закупки с приближающимися дедлайнами.
    
    Args:
        df: DataFrame с данными
        days_ahead: количество дней вперёд
        
    Returns:
        DataFrame с закупками
    """
    df = df.copy()
    df['deadline_dt'] = pd.to_datetime(df['deadline_date'], format='%d.%m.%Y', errors='coerce')
    
    today = datetime.now()
    future_date = today + timedelta(days=days_ahead)
    
    mask = (df['deadline_dt'] >= today) & (df['deadline_dt'] <= future_date)
    upcoming = df[mask].copy()
    
    if len(upcoming) > 0:
        upcoming['days_left'] = (upcoming['deadline_dt'] - today).dt.days
        upcoming = upcoming.sort_values('days_left')
    
    return upcoming


def calculate_time_to_deadline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавить колонку с количеством дней до дедлайна.
    
    Args:
        df: DataFrame с данными
        
    Returns:
        DataFrame с новой колонкой deadline_days
    """
    df = df.copy()
    df['deadline_days'] = calculate_deadline_days(df)
    return df


def get_publication_timeline(df: pd.DataFrame, freq: str = 'D') -> pd.Series:
    """
    Временной ряд публикаций закупок.
    
    Args:
        df: DataFrame с данными
        freq: частота ('D' - день, 'W' - неделя, 'M' - месяц)
        
    Returns:
        Series с количеством публикаций по периодам
    """
    df = df.copy()
    df['pub_date'] = pd.to_datetime(df['published_date'], format='%d.%m.%Y', errors='coerce')
    df = df.dropna(subset=['pub_date'])
    
    if len(df) == 0:
        return pd.Series()
    
    timeline = df.set_index('pub_date').resample(freq).size()
    return timeline


# Пример использования
if __name__ == "__main__":
    import json
    
    # Загружаем обогащённые данные
    with open('data/lots_enriched_100_20260425_212020.json', 'r', encoding='utf-8') as f:
        lots = json.load(f)
    
    df = pd.DataFrame(lots)
    
    # Запускаем анализ
    results = analyze_temporal_patterns(df)
    
    print("="*60)
    print("ВРЕМЕННОЙ АНАЛИЗ")
    print("="*60)
    
    # Дедлайны
    deadline = results['deadline_analysis']
    print(f"\nСредний срок подачи: {deadline['mean']:.1f} дней")
    print(f"Медиана: {deadline['median']:.1f} дней")
    print(f"Диапазон: {deadline['min']}-{deadline['max']} дней")
    
    print("\nРаспределение:")
    for label, data in deadline['distribution'].items():
        print(f"  {label}: {data['count']} ({data['percentage']:.1f}%)")
    
    # Публикации
    pub = results['publication_analysis']
    print(f"\nПериод: {pub['date_range']['start']} - {pub['date_range']['end']}")
    print(f"Всего лотов: {pub['total_lots']}")
    print(f"В среднем в день: {pub['avg_per_day']:.1f}")
    
    print("\nПо дням недели:")
    for day, count in sorted(pub['by_weekday'].items(), key=lambda x: -x[1])[:5]:
        print(f"  {day}: {count}")
