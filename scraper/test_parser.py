"""
Тестовый скрипт для исследования структуры данных zakupki.gov.ru
Цель: понять, как парсить данные о закупках
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import Dict, List, Optional
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_search_page(region_code: str = "54", page: int = 1) -> Optional[str]:
    """
    Получить HTML страницы поиска закупок
    
    Args:
        region_code: код региона (54 - Новосибирская область)
        page: номер страницы
    
    Returns:
        HTML содержимое страницы или None при ошибке
    """
    url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"
    
    params = {
        'morphology': 'on',
        'search-filter': 'Дате+размещения',
        'pageNumber': page,
        'sortDirection': 'false',
        'recordsPerPage': '_10',
        'showLotsInfoHidden': 'false',
        'sortBy': 'UPDATE_DATE',
        'fz44': 'on',
        'fz223': 'on',
        'af': 'on',
        'ca': 'on',
        'pc': 'on',
        'pa': 'on',
        'customerPlace': f'{region_code}000000000',  # Код региона
        'publishDateFrom': '25.01.2026',  # Последние 3 месяца
        'publishDateTo': '25.04.2026'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
    }
    
    try:
        logger.info(f"Запрос страницы {page} для региона {region_code}")
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info(f"Успешно получена страница {page}, размер: {len(response.text)} байт")
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе: {e}")
        return None


def parse_lot_from_card(card_html: BeautifulSoup) -> Optional[Dict]:
    """
    Парсинг данных одного лота из карточки на странице поиска
    
    Args:
        card_html: BeautifulSoup объект карточки лота
    
    Returns:
        Словарь с данными лота или None
    """
    try:
        lot_data = {}
        
        # Номер закупки
        reg_number_elem = card_html.select_one('div.registry-entry__header-mid__number a')
        if reg_number_elem:
            lot_data['reg_number'] = reg_number_elem.text.strip().replace('№ ', '')
            lot_data['url'] = 'https://zakupki.gov.ru' + reg_number_elem.get('href', '')
        
        # Объект закупки
        object_elem = card_html.select_one('div.registry-entry__body-value')
        if object_elem:
            lot_data['object_name'] = object_elem.text.strip()
        
        # Заказчик
        customer_elem = card_html.select_one('div.registry-entry__body-href a')
        if customer_elem:
            lot_data['customer_name'] = customer_elem.text.strip()
        
        # Начальная цена
        price_elem = card_html.select_one('div.price-block__value')
        if price_elem:
            price_text = price_elem.text.strip().replace(' ', '').replace(',', '.').replace('₽', '')
            try:
                lot_data['initial_price'] = float(price_text)
            except ValueError:
                lot_data['initial_price'] = None
        
        # Статус/этап
        status_elem = card_html.select_one('div.registry-entry__header-mid__title')
        if status_elem:
            lot_data['status'] = status_elem.text.strip()
        
        # Способ определения поставщика
        method_elem = card_html.select_one('div.registry-entry__header-top__title')
        if method_elem:
            lot_data['purchase_method'] = method_elem.text.strip()
        
        # Даты
        date_elems = card_html.select('div.data-block__value')
        if len(date_elems) >= 2:
            lot_data['published_date'] = date_elems[0].text.strip() if date_elems[0] else None
            lot_data['updated_date'] = date_elems[1].text.strip() if len(date_elems) > 1 else None
        
        return lot_data if lot_data else None
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге карточки лота: {e}")
        return None


def parse_search_results(html: str) -> List[Dict]:
    """
    Парсинг всех лотов со страницы результатов поиска
    
    Args:
        html: HTML содержимое страницы
    
    Returns:
        Список словарей с данными лотов
    """
    soup = BeautifulSoup(html, 'lxml')
    lots = []
    
    # Ищем все карточки закупок
    cards = soup.select('div.search-registry-entry-block')
    logger.info(f"Найдено карточек на странице: {len(cards)}")
    
    for card in cards:
        lot_data = parse_lot_from_card(card)
        if lot_data:
            lots.append(lot_data)
            logger.debug(f"Спарсен лот: {lot_data.get('reg_number', 'N/A')}")
    
    return lots


def main():
    """Основная функция для тестирования парсинга"""
    logger.info("=" * 80)
    logger.info("НАЧАЛО ТЕСТОВОГО ПАРСИНГА ZAKUPKI.GOV.RU")
    logger.info("=" * 80)
    
    # Тестируем на Новосибирской области
    region_code = "54"
    
    # Получаем первую страницу
    html = get_search_page(region_code=region_code, page=1)
    
    if not html:
        logger.error("Не удалось получить HTML страницы")
        return
    
    # Сохраняем HTML для анализа
    with open('data/test_page.html', 'w', encoding='utf-8') as f:
        f.write(html)
    logger.info("HTML страницы сохранен в data/test_page.html")
    
    # Парсим результаты
    lots = parse_search_results(html)
    
    logger.info(f"\nВсего спарсено лотов: {len(lots)}")
    
    if lots:
        # Сохраняем в JSON
        output_file = 'data/test_lots.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(lots, f, ensure_ascii=False, indent=2)
        logger.info(f"Данные сохранены в {output_file}")
        
        # Выводим первый лот для проверки
        logger.info("\n" + "=" * 80)
        logger.info("ПРИМЕР ПЕРВОГО СПАРСЕННОГО ЛОТА:")
        logger.info("=" * 80)
        print(json.dumps(lots[0], ensure_ascii=False, indent=2))
    else:
        logger.warning("Не удалось спарсить ни одного лота. Проверьте HTML структуру.")
    
    logger.info("\n" + "=" * 80)
    logger.info("ТЕСТОВЫЙ ПАРСИНГ ЗАВЕРШЕН")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
