"""
Основной модуль для парсинга данных о закупках с zakupki.gov.ru
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import random
import logging
from typing import Dict, List, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ZakupkiScraper:
    """Класс для парсинга данных с zakupki.gov.ru"""
    
    BASE_URL = "https://zakupki.gov.ru"
    SEARCH_URL = f"{BASE_URL}/epz/order/extendedsearch/results.html"
    
    # Коды регионов
    REGIONS = {
        "54": "Новосибирская область",
        "77": "Москва",
        "50": "Московская область"
    }
    
    def __init__(self, delay_min: int = 2, delay_max: int = 5):
        """
        Инициализация скрейпера
        
        Args:
            delay_min: минимальная задержка между запросами (сек)
            delay_max: максимальная задержка между запросами (сек)
        """
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
        })
    
    def _random_delay(self):
        """Случайная задержка между запросами"""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug(f"Задержка {delay:.2f} сек")
        time.sleep(delay)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _make_request(self, url: str, params: Dict = None) -> Optional[str]:
        """
        Выполнить HTTP запрос с retry-логикой
        
        Args:
            url: URL для запроса
            params: параметры запроса
        
        Returns:
            HTML содержимое или None при ошибке
        """
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе {url}: {e}")
            raise
    
    def fetch_search_page(
        self,
        region_code: str,
        date_from: str,
        date_to: str,
        page: int = 1,
        records_per_page: int = 10
    ) -> Optional[str]:
        """
        Получить страницу результатов поиска
        
        Args:
            region_code: код региона (54, 77, 50)
            date_from: дата начала в формате DD.MM.YYYY
            date_to: дата окончания в формате DD.MM.YYYY
            page: номер страницы
            records_per_page: количество записей на странице (10, 20, 50)
        
        Returns:
            HTML содержимое страницы
        """
        params = {
            'morphology': 'on',
            'search-filter': 'Дате+размещения',
            'pageNumber': page,
            'sortDirection': 'false',
            'recordsPerPage': f'_{records_per_page}',
            'showLotsInfoHidden': 'false',
            'sortBy': 'UPDATE_DATE',
            'fz44': 'on',
            'fz223': 'on',
            'af': 'on',
            'ca': 'on',
            'pc': 'on',
            'pa': 'on',
            'customerPlace': f'{region_code}000000000',
            'publishDateFrom': date_from,
            'publishDateTo': date_to
        }
        
        logger.info(f"Запрос страницы {page} для региона {self.REGIONS.get(region_code, region_code)}")
        html = self._make_request(self.SEARCH_URL, params)
        
        if html:
            self._random_delay()
        
        return html
    
    def parse_lot_card(self, card: BeautifulSoup) -> Optional[Dict]:
        """
        Парсинг одной карточки лота
        
        Args:
            card: BeautifulSoup объект карточки
        
        Returns:
            Словарь с данными лота
        """
        try:
            lot = {}
            
            # Номер закупки
            reg_number_elem = card.select_one('div.registry-entry__header-mid__number a')
            if reg_number_elem:
                lot['reg_number'] = reg_number_elem.text.strip().replace('№ ', '')
                lot['url'] = self.BASE_URL + reg_number_elem.get('href', '')
            else:
                return None
            
            # Закон (44-ФЗ или 223-ФЗ)
            method_elem = card.select_one('div.registry-entry__header-top__title')
            if method_elem:
                method_text = method_elem.text.strip()
                lot['law'] = '44-ФЗ' if '44-ФЗ' in method_text else '223-ФЗ' if '223-ФЗ' in method_text else 'Другое'
                lot['purchase_method'] = method_text.replace('\n', ' ').strip()
            
            # Статус
            status_elem = card.select_one('div.registry-entry__header-mid__title')
            if status_elem:
                lot['status'] = status_elem.text.strip()
            
            # Объект закупки
            object_elem = card.select_one('div.registry-entry__body-value')
            if object_elem:
                lot['object_name'] = object_elem.text.strip()
            
            # Заказчик
            customer_elem = card.select_one('div.registry-entry__body-href a')
            if customer_elem:
                lot['customer_name'] = customer_elem.text.strip()
                lot['customer_url'] = self.BASE_URL + customer_elem.get('href', '')
            
            # Начальная цена - улучшенный парсинг
            price_elem = card.select_one('div.price-block__value')
            if price_elem:
                price_text = price_elem.text.strip()
                # Убираем все пробелы, запятые заменяем на точки, убираем валюту
                price_clean = price_text.replace(' ', '').replace('\xa0', '').replace(',', '.').replace('₽', '').strip()
                try:
                    lot['initial_price'] = float(price_clean)
                except (ValueError, AttributeError):
                    lot['initial_price'] = None
            else:
                lot['initial_price'] = None
            
            # Даты
            date_blocks = card.select('div.data-block')
            for block in date_blocks:
                label_elem = block.select_one('div.data-block__label')
                value_elem = block.select_one('div.data-block__value')
                
                if label_elem and value_elem:
                    label = label_elem.text.strip()
                    value = value_elem.text.strip()
                    
                    if 'Размещено' in label:
                        lot['published_date'] = value
                    elif 'Обновлено' in label:
                        lot['updated_date'] = value
                    elif 'Окончание подачи заявок' in label:
                        lot['deadline_date'] = value
            
            # Timestamp парсинга
            lot['scraped_at'] = datetime.now().isoformat()
            
            return lot
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге карточки: {e}")
            return None
    
    def parse_search_results(self, html: str) -> List[Dict]:
        """
        Парсинг всех лотов со страницы
        
        Args:
            html: HTML содержимое страницы
        
        Returns:
            Список словарей с данными лотов
        """
        soup = BeautifulSoup(html, 'lxml')
        cards = soup.select('div.search-registry-entry-block')
        
        logger.info(f"Найдено карточек: {len(cards)}")
        
        lots = []
        for card in cards:
            lot = self.parse_lot_card(card)
            if lot:
                lots.append(lot)
        
        return lots
    
    def scrape_region(
        self,
        region_code: str,
        date_from: str,
        date_to: str,
        max_pages: int = 10
    ) -> List[Dict]:
        """
        Собрать данные по региону
        
        Args:
            region_code: код региона
            date_from: дата начала (DD.MM.YYYY)
            date_to: дата окончания (DD.MM.YYYY)
            max_pages: максимальное количество страниц для парсинга
        
        Returns:
            Список всех спарсенных лотов
        """
        all_lots = []
        
        logger.info(f"Начало сбора данных для региона: {self.REGIONS.get(region_code, region_code)}")
        logger.info(f"Период: {date_from} - {date_to}")
        
        for page in range(1, max_pages + 1):
            try:
                html = self.fetch_search_page(region_code, date_from, date_to, page)
                
                if not html:
                    logger.warning(f"Не удалось получить страницу {page}")
                    break
                
                lots = self.parse_search_results(html)
                
                if not lots:
                    logger.info(f"Страница {page} пустая, завершаем сбор")
                    break
                
                all_lots.extend(lots)
                logger.info(f"Страница {page}: собрано {len(lots)} лотов. Всего: {len(all_lots)}")
                
            except Exception as e:
                logger.error(f"Ошибка на странице {page}: {e}")
                break
        
        logger.info(f"Регион {self.REGIONS.get(region_code, region_code)}: собрано {len(all_lots)} лотов")
        return all_lots
    
    def scrape_all_regions(
        self,
        date_from: str,
        date_to: str,
        max_pages_per_region: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        Собрать данные по всем регионам
        
        Args:
            date_from: дата начала (DD.MM.YYYY)
            date_to: дата окончания (DD.MM.YYYY)
            max_pages_per_region: максимум страниц на регион
        
        Returns:
            Словарь {код_региона: список_лотов}
        """
        results = {}
        
        for region_code in self.REGIONS.keys():
            lots = self.scrape_region(region_code, date_from, date_to, max_pages_per_region)
            results[region_code] = lots
            
            # Сохраняем промежуточный результат
            filename = f"data/lots_{region_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(lots, f, ensure_ascii=False, indent=2)
            logger.info(f"Данные региона {region_code} сохранены в {filename}")
        
        return results


def main():
    """Основная функция для запуска парсера"""
    logger.info("=" * 80)
    logger.info("ЗАПУСК ПАРСЕРА ZAKUPKI.GOV.RU")
    logger.info("=" * 80)
    
    # Создаем папку для логов если её нет
    import os
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # Инициализируем скрейпер
    scraper = ZakupkiScraper(delay_min=2, delay_max=5)
    
    # Параметры сбора
    date_from = "25.01.2026"  # Последние 3 месяца
    date_to = "25.04.2026"
    max_pages = 5  # По 5 страниц на регион = 50 лотов * 3 региона = 150 лотов
    
    # Собираем данные
    results = scraper.scrape_all_regions(date_from, date_to, max_pages)
    
    # Объединяем все результаты
    all_lots = []
    for region_code, lots in results.items():
        for lot in lots:
            lot['region_code'] = region_code
            lot['region_name'] = scraper.REGIONS[region_code]
        all_lots.extend(lots)
    
    # Сохраняем общий файл
    output_file = f"data/lots_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_lots, f, ensure_ascii=False, indent=2)
    
    logger.info("=" * 80)
    logger.info(f"ПАРСИНГ ЗАВЕРШЕН")
    logger.info(f"Всего собрано лотов: {len(all_lots)}")
    logger.info(f"Данные сохранены в: {output_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
