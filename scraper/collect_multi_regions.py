"""
Массовый сбор данных по всем крупным регионам России.
Расширенные временные рамки: 60 дней.
"""

import sys
import io
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(str(Path(__file__).parent.parent))

from scraper.fetch_lots_enhanced import ZakupkiScraperEnhanced
from scraper.regions import REGIONS_EXTENDED

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Массовый сбор данных по всем регионам"""
    
    logger.info("="*60)
    logger.info("МАССОВЫЙ СБОР ДАННЫХ ПО ВСЕМ РЕГИОНАМ")
    logger.info("="*60)
    logger.info(f"Регионов: {len(REGIONS_EXTENDED)}")
    logger.info(f"Период: 60 дней")
    logger.info(f"Страниц на регион: 50")
    logger.info("="*60 + "\n")
    
    # Расширенный период - 60 дней
    date_to = datetime.now()
    date_from = date_to - timedelta(days=60)
    date_from_str = date_from.strftime('%d.%m.%Y')
    date_to_str = date_to.strftime('%d.%m.%Y')
    
    logger.info(f"Период сбора: {date_from_str} - {date_to_str}\n")
    
    # Оценка времени
    total_pages = len(REGIONS_EXTENDED) * 50
    estimated_time = (total_pages * 3) / 60  # минуты
    
    logger.info(f"Ожидаемое время: ~{estimated_time:.0f} минут")
    logger.info(f"Ожидаемое количество лотов: ~{len(REGIONS_EXTENDED) * 500}\n")
    
    print("\n[INFO] Запуск массового сбора данных...")
    print(f"Регионов: {len(REGIONS_EXTENDED)}")
    print(f"Ожидаемое время: ~{estimated_time:.0f} минут")
    print(f"Ожидаемое количество лотов: ~{len(REGIONS_EXTENDED) * 500}")
    print("\nДля остановки нажмите Ctrl+C\n")
    
    # Автоматический запуск без подтверждения
    import time
    time.sleep(2)  # Небольшая пауза для чтения информации
    
    # Парсер в быстром режиме
    scraper = ZakupkiScraperEnhanced(
        delay_min=2,
        delay_max=4,
        fetch_details=False
    )
    
    all_lots = []
    region_stats = {}
    
    try:
        for i, (region_code, region_name) in enumerate(REGIONS_EXTENDED.items(), 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i}/{len(REGIONS_EXTENDED)}] Регион: {region_name} (код {region_code})")
            logger.info(f"{'='*60}\n")
            
            try:
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
                region_stats[region_code] = {
                    'name': region_name,
                    'lots': len(lots)
                }
                
                logger.info(f"✓ {region_name}: {len(lots)} лотов")
                logger.info(f"Всего собрано: {len(all_lots)} лотов\n")
                
                # Промежуточное сохранение каждые 3 региона
                if i % 3 == 0:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    temp_filename = f"data/lots_multi_temp_{timestamp}.json"
                    
                    with open(temp_filename, 'w', encoding='utf-8') as f:
                        json.dump(all_lots, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"💾 Промежуточное сохранение: {temp_filename}\n")
                
            except Exception as e:
                logger.error(f"Ошибка при сборе данных для региона {region_code}: {e}")
                continue
        
        # Финальное сохранение
        logger.info(f"\n{'='*60}")
        logger.info(f"СБОР ЗАВЕРШЁН: {len(all_lots)} лотов")
        logger.info(f"{'='*60}\n")
        
        if all_lots:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/lots_multi_regions_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_lots, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Данные сохранены: {filename}")
            
            # Статистика по регионам
            logger.info("\n📊 Статистика по регионам:")
            for code, stats in region_stats.items():
                logger.info(f"  {stats['name']}: {stats['lots']} лотов")
            
            # Общая статистика
            law_44 = sum(1 for lot in all_lots if lot.get('law') == '44-ФЗ')
            law_223 = sum(1 for lot in all_lots if lot.get('law') == '223-ФЗ')
            
            logger.info(f"\n📈 По законам:")
            logger.info(f"  44-ФЗ: {law_44} ({law_44/len(all_lots)*100:.1f}%)")
            logger.info(f"  223-ФЗ: {law_223} ({law_223/len(all_lots)*100:.1f}%)")
            
            # Средняя цена
            prices = [lot['initial_price'] for lot in all_lots if lot.get('initial_price')]
            if prices:
                avg_price = sum(prices) / len(prices)
                total_volume = sum(prices)
                logger.info(f"\n💰 Финансы:")
                logger.info(f"  Средняя цена: {avg_price:,.0f} ₽")
                logger.info(f"  Общий объём: {total_volume:,.0f} ₽")
        
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Прервано пользователем")
        logger.info(f"Собрано лотов: {len(all_lots)}")
        
        if all_lots:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/lots_multi_partial_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_lots, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Частичные данные сохранены: {filename}")
    
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    main()
