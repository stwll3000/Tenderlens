"""
Модуль аналитики для TenderLens.

Содержит функции для анализа данных о госзакупках:
- pricing: анализ цен и снижения стоимости
- competition: анализ конкуренции и рыночной концентрации
"""

from . import pricing
from . import competition

__all__ = ['pricing', 'competition']
