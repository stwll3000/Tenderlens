"""
Улучшенный парсер с извлечением дополнительных полей из детальных страниц закупок.
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
from pathlib import Path

from scraper.regions import REGIONS_EXTENDED

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


class ZakupkiScraperEnhanced:
    """Улучшенный класс для парсинга данных с zakupki.gov.ru с детальной информацией"""
    
    BASE_URL = "https://zakupki.gov.ru"
    SEARCH_URL = f"{BASE_URL}/epz/order/extendedsearch/results.html"
    
    # Используем расширенный список регионов
    REGIONS = REGIONS_EXTENDED
    
    def __init__(self, delay_min: int = 2, delay_max: int = 5, fetch_details: bool = True):
        """
        Инициализация скрейпера
        
        Args:
            delay_min: минимальная задержка между запросами (сек)
            delay_max: максимальная задержка между запросами (сек)
            fetch_details: парсить ли детальные страницы (даты, ОКПД2)
        """
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.fetch_details = fetch_details
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
    
    def fetch_lot_details(self, lot_url: str) -> Dict:
        """
        Получить детальную информацию о закупке (даты, ОКПД2, участники)
        
        Args:
            lot_url: URL страницы закупки
        
        Returns:
            Словарь с дополнительными полями
        """
        details = {
            'published_date': None,
            'updated_date': None,
            'deadline_date': None,
            'okpd2_codes': [],
            'participants_count': None
        }
        
        try:
            self._random_delay()
            html = self._make_request(lot_url)
            
            if not html:
                return details
            
            soup = BeautifulSoup(html, 'lxml')
            
            # Парсинг дат
            date_titles = soup.find_all('span', class_='cardMainInfo__title')
            
            for title in date_titles:
                title_text = title.get_text(strip=True)
                content = title.find_next_sibling('span', class_='cardMainInfo__content')
                
                if content:
                    date_value = content.get_text(strip=True)
                    
                    if 'Размещено' in title_text:
                        details['published_date'] = date_value
                    elif 'Обновлено' in title_text:
                        details['updated_date'] = date_value
                    elif 'Окончание подачи заявок' in title_text:
                        details['deadline_date'] = date_value
            
            # Парсинг ОКПД2 кодов
            tables = soup.find_all('table')
            
            for table in tables:
                headers = [th.get_text(strip=True) for th in table.find_all('th')]
                
                # Ищем таблицу с позициями
                if any('Код позиции' in h or 'ОКПД' in h for h in headers):
                    tbody = table.find('tbody')
                    if tbody:
                        rows = tbody.find_all('tr')
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) >= 2:
                                # ОКПД2 код обычно во второй ячейке
                                okpd_text = cells[1].get_text(strip=True)
                                # Код ОКПД2 имеет формат XX.XX.XX.XXX
                                if okpd_text and '.' in okpd_text and len(okpd_text) <= 20:
                                    details['okpd2_codes'].append(okpd_text)
            
            # Парсинг количества участников (если закупка завершена)
            # Это требует перехода на вкладку протокола, пока оставим None
            
            logger.debug(f"Детали получены: {details}")
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге деталей {lot_url}: {e}")
        
        return details
    
    def parse_lot_card(self, card) -> Optional[Dict]:
        """
        Парсинг одной карточки лота из результатов поиска
        
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
            
            # Начальная цена
            price_elem = card.select_one('div.price-block__value')
            if price_elem:
                price_text = price_elem.text.strip()
                price_clean = price_text.replace(' ', '').replace('\xa0', '').replace(',', '.').replace('₽', '').strip()
                try:
                    lot['initial_price'] = float(price_clean)
                except (ValueError, AttributeError):
                    lot['initial_price'] = None
            else:
                lot['initial_price'] = None
            
            # Timestamp парсинга
            lot['scraped_at'] = datetime.now().isoformat()
            
            # Получаем детальную информацию, если включено
            if self.fetch_details and lot.get('url'):
                logger.info(f"Получение деталей для {lot['reg_number']}")
                details = self.fetch_lot_details(lot['url'])
                lot.update(details)
            
            return lot
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге карточки: {e}")
            return None
    
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
            date_from: дата начала (формат DD.MM.YYYY)
            date_to: дата окончания (формат DD.MM.YYYY)
            page: номер страницы
            records_per_page: количество записей на странице
        
        Returns:
            HTML содержимое страницы или None
        """
        params = {
            'morphology': 'on',
            'search-filter': 'Дате размещения',
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
            'currencyIdGeneral': '-1',
            'publishDateFrom': date_from,
            'publishDateTo': date_to,
            'regionIds': region_code,
        }
        
        try:
            self._random_delay()
            html = self._make_request(self.SEARCH_URL, params=params)
            return html
        except Exception as e:
            logger.error(f"Ошибка при получении страницы {page}: {e}")
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
    
    def fetch_all_lots(
        self,
        region_code: str,
        date_from: str,
        date_to: str,
        max_pages: int = 50,
        records_per_page: int = 10
    ) -> List[Dict]:
        """
        Собрать все лоты для региона за период
        
        Args:
            region_code: код региона
            date_from: дата начала (DD.MM.YYYY)
            date_to: дата окончания (DD.MM.YYYY)
            max_pages: максимальное количество страниц
            records_per_page: записей на странице
        
        Returns:
            Список всех собранных лотов
        """
        all_lots = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"Обработка страницы {page}/{max_pages}")
            
            html = self.fetch_search_page(
                region_code=region_code,
                date_from=date_from,
                date_to=date_to,
                page=page,
                records_per_page=records_per_page
            )
            
            if not html:
                logger.warning(f"Не удалось получить страницу {page}, пропускаем")
                continue
            
            lots = self.parse_search_results(html)
            
            if not lots:
                logger.info(f"Страница {page} пустая, завершаем сбор")
                break
            
            all_lots.extend(lots)
            logger.info(f"Собрано лотов: {len(all_lots)}")
        
        return all_lots


# Пример использования
if __name__ == "__main__":
    # Тест на одной закупке
    scraper = ZakupkiScraperEnhanced(delay_min=2, delay_max=3, fetch_details=True)
    
    test_url = "https://zakupki.gov.ru/epz/order/notice/zk20/view/common-info.html?regNumber=0851600011226000009"
    
    print("Testing detail extraction...")
    details = scraper.fetch_lot_details(test_url)
    
    print("\nExtracted details:")
    print(json.dumps(details, indent=2, ensure_ascii=False))
