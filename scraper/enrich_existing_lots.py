"""
Обогащение существующих лотов детальной информацией (даты, ОКПД2).
Берёт лоты из JSON и добавляет к ним данные со страниц деталей.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import random
import logging
from typing import Dict, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/enrichment.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LotEnricher:
    """Класс для обогащения лотов детальной информацией"""
    
    BASE_URL = "https://zakupki.gov.ru"
    
    def __init__(self, delay_min: int = 2, delay_max: int = 5):
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _random_delay(self):
        """Случайная задержка между запросами"""
        delay = random.uniform(self.delay_min, self.delay_max)
        time.sleep(delay)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError))
    )
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Получение страницы с retry-логикой"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Ошибка при загрузке {url}: {e}")
            raise
    
    def _extract_date(self, soup: BeautifulSoup, label: str) -> Optional[str]:
        """Извлечение даты по метке"""
        try:
            # Ищем по тексту в заголовках
            elements = soup.find_all('span', class_='cardMainInfo__title')
            for elem in elements:
                if label.lower() in elem.get_text().lower():
                    # Ищем следующий элемент с датой
                    next_elem = elem.find_next_sibling()
                    if next_elem:
                        date_text = next_elem.get_text(strip=True)
                        # Извлекаем только дату (DD.MM.YYYY)
                        if len(date_text) >= 10:
                            return date_text[:10]
            
            # Альтернативный поиск в section__title
            elements = soup.find_all('span', class_='section__title')
            for elem in elements:
                if label.lower() in elem.get_text().lower():
                    # Ищем следующий элемент
                    parent = elem.parent
                    if parent:
                        next_elem = parent.find_next_sibling()
                        if next_elem:
                            date_text = next_elem.get_text(strip=True)
                            # Извлекаем дату из формата "25.04.2026 23:45(МСК+9)"
                            if len(date_text) >= 10:
                                return date_text[:10]
            
            return None
        except Exception as e:
            logger.debug(f"Ошибка извлечения даты '{label}': {e}")
            return None
    
    def _extract_okpd2(self, soup: BeautifulSoup) -> list:
        """Извлечение кодов ОКПД2"""
        try:
            okpd2_codes = []
            # Ищем таблицу с ОКПД2
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        # Проверяем, есть ли код ОКПД2 (формат: XX.XX.XX.XXX)
                        code_text = cells[0].get_text(strip=True)
                        if '.' in code_text and len(code_text) <= 15:
                            okpd2_codes.append(code_text)
            return okpd2_codes[:5]  # Максимум 5 кодов
        except Exception as e:
            logger.debug(f"Ошибка извлечения ОКПД2: {e}")
            return []
    
    def enrich_lot(self, lot: Dict) -> Dict:
        """
        Обогащение одного лота детальной информацией
        
        Args:
            lot: словарь с базовой информацией о лоте
            
        Returns:
            обогащённый словарь
        """
        url = lot.get('url')
        if not url:
            logger.warning(f"Лот без URL: {lot.get('reg_number')}")
            return lot
        
        try:
            logger.info(f"Обогащение лота {lot.get('reg_number')}...")
            
            # Задержка перед запросом
            self._random_delay()
            
            # Загружаем страницу
            soup = self._fetch_page(url)
            if not soup:
                return lot
            
            # Извлекаем даты
            published_date = self._extract_date(soup, 'Размещено')
            updated_date = self._extract_date(soup, 'Обновлено')
            deadline_date = self._extract_date(soup, 'Окончание подачи')
            
            # Извлекаем ОКПД2
            okpd2_codes = self._extract_okpd2(soup)
            
            # Добавляем новые поля
            enriched_lot = lot.copy()
            enriched_lot['published_date'] = published_date
            enriched_lot['updated_date'] = updated_date
            enriched_lot['deadline_date'] = deadline_date
            enriched_lot['okpd2_codes'] = okpd2_codes
            enriched_lot['enriched_at'] = datetime.now().isoformat()
            
            logger.info(f"✓ Лот {lot.get('reg_number')} обогащён")
            return enriched_lot
            
        except Exception as e:
            logger.error(f"Ошибка обогащения лота {lot.get('reg_number')}: {e}")
            return lot
    
    def enrich_lots_from_file(
        self, 
        input_file: str, 
        output_file: str, 
        max_lots: int = 100,
        save_every: int = 10
    ):
        """
        Обогащение лотов из JSON-файла
        
        Args:
            input_file: путь к исходному файлу
            output_file: путь для сохранения результата
            max_lots: максимальное количество лотов для обогащения
            save_every: сохранять промежуточные результаты каждые N лотов
        """
        logger.info(f"Загрузка лотов из {input_file}...")
        
        with open(input_file, 'r', encoding='utf-8') as f:
            lots = json.load(f)
        
        total = min(len(lots), max_lots)
        logger.info(f"Будет обогащено {total} лотов из {len(lots)}")
        
        enriched_lots = []
        
        for i, lot in enumerate(lots[:max_lots], 1):
            logger.info(f"\n[{i}/{total}] Обработка лота...")
            
            enriched_lot = self.enrich_lot(lot)
            enriched_lots.append(enriched_lot)
            
            # Промежуточное сохранение
            if i % save_every == 0:
                logger.info(f"Промежуточное сохранение ({i} лотов)...")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(enriched_lots, f, ensure_ascii=False, indent=2)
        
        # Финальное сохранение
        logger.info(f"\nСохранение результатов в {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enriched_lots, f, ensure_ascii=False, indent=2)
        
        # Статистика
        enriched_count = sum(1 for lot in enriched_lots if lot.get('published_date'))
        logger.info(f"\n{'='*60}")
        logger.info(f"ЗАВЕРШЕНО!")
        logger.info(f"{'='*60}")
        logger.info(f"Всего обработано: {len(enriched_lots)}")
        logger.info(f"Успешно обогащено: {enriched_count}")
        logger.info(f"Процент успеха: {enriched_count/len(enriched_lots)*100:.1f}%")
        logger.info(f"Файл сохранён: {output_file}")


def main():
    """Основная функция"""
    
    # Пути к файлам
    input_file = "data/lots_multi_regions_6000_20260425.json"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"data/lots_enriched_{timestamp}.json"
    
    # Создаём директорию для логов
    Path("logs").mkdir(exist_ok=True)
    
    # Создаём enricher
    enricher = LotEnricher(delay_min=2, delay_max=5)
    
    # Обогащаем первые 100 лотов
    enricher.enrich_lots_from_file(
        input_file=input_file,
        output_file=output_file,
        max_lots=100,
        save_every=10
    )


if __name__ == "__main__":
    main()
