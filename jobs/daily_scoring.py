"""
Ежедневный скрипт для обновления benchmark'ов и скоринга лотов.

Запускается каждое утро (например, в 06:00) и выполняет:
1. Обновление niche_slug для новых лотов
2. Пересчёт price benchmarks
3. Скоринг всех активных лотов
4. Получение протоколов для завершённых лотов

Использование:
    python jobs/daily_scoring.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from db.connection import get_session
from features.niche_mapping import update_lot_niches, init_niche_categories
from analytics.benchmark import compute_all_benchmarks
from analytics.profit import score_all_lots
from scraper.fetch_protocols import fetch_protocols_for_lots

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_scoring.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_daily_scoring():
    """Основная функция ежедневного скоринга."""
    
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info(f"Начало ежедневного скоринга: {start_time}")
    logger.info("=" * 80)
    
    with get_session() as session:
        
        # Шаг 1: Инициализация категорий (если ещё не сделано)
        logger.info("\n[1/5] Инициализация категорий лотов...")
        try:
            count = init_niche_categories(session)
            logger.info(f"Добавлено категорий: {count}")
        except Exception as e:
            logger.error(f"Ошибка при инициализации категорий: {e}")
        
        # Шаг 2: Обновление niche_slug для новых лотов
        logger.info("\n[2/5] Обновление niche_slug для лотов...")
        try:
            updated = update_lot_niches(session, batch_size=1000)
            logger.info(f"Обновлено лотов: {updated}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении niche_slug: {e}")
        
        # Шаг 3: Получение протоколов для завершённых лотов
        logger.info("\n[3/5] Получение протоколов итогов...")
        try:
            protocol_stats = fetch_protocols_for_lots(session, limit=50)
            logger.info(
                f"Протоколы: обработано={protocol_stats['processed']}, "
                f"успешно={protocol_stats['success']}, ошибок={protocol_stats['failed']}"
            )
        except Exception as e:
            logger.error(f"Ошибка при получении протоколов: {e}")
        
        # Шаг 4: Пересчёт price benchmarks
        logger.info("\n[4/5] Пересчёт price benchmarks...")
        try:
            benchmark_stats = compute_all_benchmarks(session, months=12, force_recompute=False)
            logger.info(
                f"Benchmarks: рассчитано={benchmark_stats['computed']}, "
                f"пропущено={benchmark_stats['skipped']}, ошибок={benchmark_stats['failed']}"
            )
        except Exception as e:
            logger.error(f"Ошибка при расчёте benchmarks: {e}")
        
        # Шаг 5: Скоринг всех активных лотов
        logger.info("\n[5/5] Скоринг активных лотов...")
        try:
            scoring_stats = score_all_lots(session, batch_size=100)
            logger.info(
                f"Скоринг: обработано={scoring_stats['scored']}, "
                f"ошибок={scoring_stats['failed']}"
            )
        except Exception as e:
            logger.error(f"Ошибка при скоринге: {e}")
    
    # Итоговая статистика
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("\n" + "=" * 80)
    logger.info(f"Ежедневный скоринг завершён: {end_time}")
    logger.info(f"Время выполнения: {duration:.1f} секунд ({duration/60:.1f} минут)")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        run_daily_scoring()
    except Exception as e:
        logger.critical(f"Критическая ошибка при выполнении скрипта: {e}", exc_info=True)
        sys.exit(1)
