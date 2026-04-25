"""
Скрипт для массового сбора данных с zakupki.gov.ru с детальной информацией.
Использует улучшенный парсер для извлечения дат и ОКПД2 кодов.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent.parent))

from scraper.fetch_lots_enhanced import ZakupkiScraperEnhanced

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect_lots_with_details(
    region_codes: list,
    max_pages: int = 50,
    records_per_page: int = 10,
    fetch_details: bool = True
):
    """
    Собрать лоты с детальной информацией
    
    Args:
        region_codes: список кодов регионов
        max_pages: максимум страниц на регион
        records_per_page: записей на страницу
        fetch_details: парсить ли детальные страницы
    """
    
    scraper = ZakupkiScraperEnhanced(
        delay_min=3,  # Увеличиваем задержку из-за детальных запросов
        delay_max=5,
        fetch_details=fetch_details
    )
    
    # Даты поиска (последние 30 дней)
    date_to = datetime.now()
    date_from = date_to - timedelta(days=30)
    
    date_from_str = date_from.strftime('%d.%m.%Y')
    date_to_str = date_to.strftime('%d.%m.%Y')
    
    all_lots = []
    
    for region_code in region_codes:
        region_name = scraper.REGIONS.get(region_code, f"Регион {region_code}")
        logger.info(f"\n{'='*60}")
        logger.info(f"Начинаем сбор для региона: {region_name} (код {region_code})")
        logger.info(f"Период: {date_from_str} - {date_to_str}")
        logger.info(f"Детальная информация: {'ДА' if fetch_details else 'НЕТ'}")
        logger.info(f"{'='*60}\n")
        
        try:
            lots = scraper.fetch_all_lots(
                region_code=region_code,
                date_from=date_from_str,
                date_to=date_to_str,
                max_pages=max_pages,
                records_per_page=records_per_page
            )
            
            logger.info(f"Собрано {len(lots)} лотов для региона {region_name}")
            
            # Добавляем регион к каждому лоту
            for lot in lots:
                lot['region_code'] = region_code
                lot['region_name'] = region_name
            
            all_lots.extend(lots)
            
        except Exception as e:
            logger.error(f"Ошибка при сборе данных для региона {region_code}: {e}")
            continue
    
    return all_lots


def main():
    """Главная функция"""
    
    # Регионы для сбора
    regions = ["54", "77", "50"]  # Новосибирск, Москва, Московская область
    
    logger.info("="*60)
    logger.info("ЗАПУСК СБОРА ДАННЫХ С ДЕТАЛЬНОЙ ИНФОРМАЦИЕЙ")
    logger.info("="*60)
    logger.info(f"Регионы: {', '.join(regions)}")
    logger.info(f"Максимум страниц на регион: 50")
    logger.info(f"Детальная информация: ДА (даты, ОКПД2)")
    logger.info("="*60 + "\n")
    
    # Предупреждение
    print("\n⚠️  ВНИМАНИЕ!")
    print("Сбор детальной информации занимает много времени:")
    print("- ~5 секунд на каждый лот")
    print("- Для 500 лотов: ~40 минут")
    print("- Для 1000 лотов: ~1.5 часа")
    print("\nВы можете прервать процесс в любой момент (Ctrl+C)")
    print("Собранные данные будут сохранены.\n")
    
    response = input("Продолжить? (yes/no): ")
    if response.lower() not in ['yes', 'y', 'да']:
        print("Отменено пользователем")
        return
    
    try:
        # Собираем данные
        lots = collect_lots_with_details(
            region_codes=regions,
            max_pages=50,
            records_per_page=10,
            fetch_details=True
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"СБОР ЗАВЕРШЁН")
        logger.info(f"Всего собрано: {len(lots)} лотов")
        logger.info(f"{'='*60}\n")
        
        # Сохраняем результаты
        if lots:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/lots_enhanced_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(lots, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Данные сохранены: {filename}")
            
            # Статистика
            with_dates = sum(1 for lot in lots if lot.get('published_date'))
            with_okpd = sum(1 for lot in lots if lot.get('okpd2_codes'))
            
            logger.info(f"\nСтатистика:")
            logger.info(f"  Лотов с датами: {with_dates} ({with_dates/len(lots)*100:.1f}%)")
            logger.info(f"  Лотов с ОКПД2: {with_okpd} ({with_okpd/len(lots)*100:.1f}%)")
        else:
            logger.warning("Нет данных для сохранения")
    
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Прервано пользователем")
        logger.info(f"Собрано лотов: {len(all_lots) if 'all_lots' in locals() else 0}")
        
        # Сохраняем то, что успели собрать
        if 'all_lots' in locals() and all_lots:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/lots_enhanced_partial_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_lots, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ Частичные данные сохранены: {filename}")
    
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise


if __name__ == "__main__":
    main()
