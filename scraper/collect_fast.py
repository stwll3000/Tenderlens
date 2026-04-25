"""
Быстрый сбор данных БЕЗ детальной информации (только карточки).
Для сбора 1000+ лотов за разумное время.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging

sys.path.append(str(Path(__file__).parent.parent))

from scraper.fetch_lots_enhanced import ZakupkiScraperEnhanced

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Быстрый сбор данных"""
    
    logger.info("="*60)
    logger.info("БЫСТРЫЙ СБОР ДАННЫХ (без детальной информации)")
    logger.info("="*60)
    logger.info("Регионы: Новосибирск, Москва, Московская область")
    logger.info("Максимум страниц: 50 на регион")
    logger.info("Ожидаемое время: ~15-20 минут")
    logger.info("="*60 + "\n")
    
    # Парсер БЕЗ детальной информации
    scraper = ZakupkiScraperEnhanced(
        delay_min=2,
        delay_max=4,
        fetch_details=False  # Быстрый режим
    )
    
    # Даты (последние 30 дней)
    date_to = datetime.now()
    date_from = date_to - timedelta(days=30)
    date_from_str = date_from.strftime('%d.%m.%Y')
    date_to_str = date_to.strftime('%d.%m.%Y')
    
    regions = ["54", "77", "50"]
    all_lots = []
    
    try:
        for region_code in regions:
            region_name = scraper.REGIONS.get(region_code)
            logger.info(f"\n{'='*60}")
            logger.info(f"Регион: {region_name} (код {region_code})")
            logger.info(f"{'='*60}\n")
            
            lots = scraper.fetch_all_lots(
                region_code=region_code,
                date_from=date_from_str,
                date_to=date_to_str,
                max_pages=50,
                records_per_page=10
            )
            
            # Добавляем регион
            for lot in lots:
                lot['region_code'] = region_code
                lot['region_name'] = region_name
            
            all_lots.extend(lots)
            logger.info(f"✓ Регион {region_name}: {len(lots)} лотов")
        
        # Сохраняем
        logger.info(f"\n{'='*60}")
        logger.info(f"СБОР ЗАВЕРШЁН: {len(all_lots)} лотов")
        logger.info(f"{'='*60}\n")
        
        if all_lots:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/lots_fast_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_lots, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Данные сохранены: {filename}")
            
            # Статистика по регионам
            logger.info("\nСтатистика по регионам:")
            for region_code in regions:
                count = sum(1 for lot in all_lots if lot.get('region_code') == region_code)
                region_name = scraper.REGIONS.get(region_code)
                logger.info(f"  {region_name}: {count} лотов")
            
            # Статистика по законам
            law_44 = sum(1 for lot in all_lots if lot.get('law') == '44-ФЗ')
            law_223 = sum(1 for lot in all_lots if lot.get('law') == '223-ФЗ')
            logger.info(f"\nПо законам:")
            logger.info(f"  44-ФЗ: {law_44} ({law_44/len(all_lots)*100:.1f}%)")
            logger.info(f"  223-ФЗ: {law_223} ({law_223/len(all_lots)*100:.1f}%)")
        
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Прервано пользователем")
        
        if all_lots:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/lots_fast_partial_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_lots, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Частичные данные сохранены: {filename}")
            logger.info(f"  Собрано: {len(all_lots)} лотов")
    
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise


if __name__ == "__main__":
    main()
