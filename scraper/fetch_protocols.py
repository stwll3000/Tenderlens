"""
Парсер протоколов итогов торгов с zakupki.gov.ru

Получает данные о результатах торгов:
- Цену победителя (final_price)
- Список всех участников с их ставками
- ИНН и названия поставщиков
- Информацию о победителе

Эти данные критически важны для расчёта Profit Score.
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import random
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.orm import Session

from db.models import Lot, Supplier, LotParticipation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/protocol_scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProtocolScraper:
    """Класс для парсинга протоколов итогов торгов."""
    
    BASE_URL = "https://zakupki.gov.ru"
    
    def __init__(self, delay_min: int = 2, delay_max: int = 5):
        """
        Инициализация скрейпера протоколов.
        
        Args:
            delay_min: минимальная задержка между запросами (сек)
            delay_max: максимальная задержка между запросами (сек)
        """
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
        })
    
    def _random_delay(self):
        """Случайная задержка между запросами."""
        delay = random.uniform(self.delay_min, self.delay_max)
        time.sleep(delay)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _make_request(self, url: str) -> Optional[str]:
        """
        Выполнить HTTP запрос с retry-логикой.
        
        Args:
            url: URL для запроса
        
        Returns:
            HTML содержимое или None при ошибке
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе {url}: {e}")
            raise
    
    def fetch_protocol(self, reg_number: str) -> Optional[Dict]:
        """
        Получает протокол итогов для лота по регистрационному номеру.
        
        Args:
            reg_number: регистрационный номер закупки
        
        Returns:
            Словарь с данными протокола или None
        """
        # URL протокола итогов (может отличаться для 44-ФЗ и 223-ФЗ)
        # Для 44-ФЗ обычно: /epz/order/notice/ea44/view/common-info.html?regNumber=...
        # Для протокола: /epz/order/notice/ea44/view/protocol-results.html?regNumber=...
        
        protocol_url = f"{self.BASE_URL}/epz/order/notice/ea44/view/protocol-results.html?regNumber={reg_number}"
        
        logger.info(f"Получаем протокол для {reg_number}")
        
        try:
            html = self._make_request(protocol_url)
            
            if not html:
                logger.warning(f"Не удалось получить протокол для {reg_number}")
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Парсим данные протокола
            protocol_data = self._parse_protocol_page(soup, reg_number)
            
            self._random_delay()
            
            return protocol_data
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге протокола {reg_number}: {e}")
            return None
    
    def _parse_protocol_page(self, soup: BeautifulSoup, reg_number: str) -> Dict:
        """
        Парсит страницу протокола итогов.
        
        Args:
            soup: BeautifulSoup объект страницы
            reg_number: регистрационный номер
        
        Returns:
            Словарь с данными протокола
        """
        data = {
            'reg_number': reg_number,
            'final_price': None,
            'winner': None,
            'participants': []
        }
        
        # Ищем таблицу с участниками
        # Структура может отличаться, нужно адаптировать под реальную разметку
        
        # Вариант 1: Таблица с классом "tableBlock"
        table = soup.find('table', class_='tableBlock')
        
        if not table:
            # Вариант 2: Ищем по заголовку
            header = soup.find(text=re.compile(r'Сведения об участниках', re.IGNORECASE))
            if header:
                table = header.find_parent('table')
        
        if table:
            rows = table.find_all('tr')[1:]  # Пропускаем заголовок
            
            for idx, row in enumerate(rows, 1):
                cells = row.find_all('td')
                
                if len(cells) >= 3:
                    participant = self._parse_participant_row(cells, idx)
                    
                    if participant:
                        data['participants'].append(participant)
                        
                        # Победитель обычно первый или помечен специально
                        if participant.get('is_winner'):
                            data['winner'] = participant
                            data['final_price'] = participant.get('bid_price')
        
        # Если не нашли победителя в таблице, ищем отдельно
        if not data['winner']:
            winner_info = self._find_winner_info(soup)
            if winner_info:
                data['winner'] = winner_info
                data['final_price'] = winner_info.get('bid_price')
        
        return data
    
    def _parse_participant_row(self, cells: List, rank: int) -> Optional[Dict]:
        """
        Парсит строку таблицы с участником.
        
        Args:
            cells: список ячеек строки
            rank: место участника
        
        Returns:
            Словарь с данными участника
        """
        try:
            # Примерная структура (нужно адаптировать):
            # [Место, Наименование, ИНН, Цена предложения, Статус]
            
            participant = {
                'rank': rank,
                'name': cells[1].get_text(strip=True) if len(cells) > 1 else None,
                'inn': self._extract_inn(cells[2].get_text(strip=True)) if len(cells) > 2 else None,
                'bid_price': self._extract_price(cells[3].get_text(strip=True)) if len(cells) > 3 else None,
                'is_winner': rank == 1,  # Обычно первый = победитель
                'rejected': False,
                'rejection_reason': None
            }
            
            # Проверяем статус (отклонён/допущен)
            if len(cells) > 4:
                status = cells[4].get_text(strip=True).lower()
                if 'отклон' in status or 'не допущ' in status:
                    participant['rejected'] = True
                    participant['rejection_reason'] = status
                    participant['is_winner'] = False
            
            return participant
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге участника: {e}")
            return None
    
    def _find_winner_info(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Ищет информацию о победителе на странице.
        
        Args:
            soup: BeautifulSoup объект
        
        Returns:
            Словарь с данными победителя
        """
        # Ищем блок с информацией о победителе
        winner_block = soup.find(text=re.compile(r'Победитель', re.IGNORECASE))
        
        if winner_block:
            parent = winner_block.find_parent('div', class_='blockInfo')
            
            if parent:
                name = parent.find(text=re.compile(r'Наименование')).find_next('td').get_text(strip=True)
                inn = parent.find(text=re.compile(r'ИНН')).find_next('td').get_text(strip=True)
                price_elem = parent.find(text=re.compile(r'Цена'))
                price = self._extract_price(price_elem.find_next('td').get_text(strip=True)) if price_elem else None
                
                return {
                    'rank': 1,
                    'name': name,
                    'inn': self._extract_inn(inn),
                    'bid_price': price,
                    'is_winner': True,
                    'rejected': False,
                    'rejection_reason': None
                }
        
        return None
    
    def _extract_inn(self, text: str) -> Optional[str]:
        """Извлекает ИНН из текста."""
        if not text:
            return None
        
        # ИНН: 10 или 12 цифр
        match = re.search(r'\b(\d{10}|\d{12})\b', text)
        return match.group(1) if match else None
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Извлекает цену из текста."""
        if not text:
            return None
        
        # Убираем все кроме цифр, точек и запятых
        cleaned = re.sub(r'[^\d.,]', '', text)
        cleaned = cleaned.replace(',', '.')
        
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def save_protocol_data(self, session: Session, protocol_data: Dict) -> bool:
        """
        Сохраняет данные протокола в БД.
        
        Args:
            session: SQLAlchemy сессия
            protocol_data: данные протокола
        
        Returns:
            True если успешно, False иначе
        """
        try:
            reg_number = protocol_data['reg_number']
            
            # Находим лот
            lot = session.query(Lot).filter_by(reg_number=reg_number).first()
            
            if not lot:
                logger.warning(f"Лот {reg_number} не найден в БД")
                return False
            
            # Обновляем final_price
            if protocol_data['final_price']:
                lot.final_price = protocol_data['final_price']
                
                # Рассчитываем price_reduction_pct
                if lot.initial_price and lot.initial_price > 0:
                    reduction = ((lot.initial_price - lot.final_price) / lot.initial_price) * 100
                    lot.price_reduction_pct = round(reduction, 2)
            
            # Сохраняем участников
            for participant_data in protocol_data['participants']:
                if not participant_data.get('inn'):
                    continue
                
                # Создаём или получаем поставщика
                supplier = session.query(Supplier).filter_by(inn=participant_data['inn']).first()
                
                if not supplier:
                    supplier = Supplier(
                        inn=participant_data['inn'],
                        name=participant_data['name'] or 'Неизвестно',
                        first_seen_at=datetime.now()
                    )
                    session.add(supplier)
                    session.flush()
                
                # Создаём запись об участии
                participation = session.query(LotParticipation).filter_by(
                    lot_id=lot.id,
                    supplier_id=supplier.id
                ).first()
                
                if not participation:
                    participation = LotParticipation(
                        lot_id=lot.id,
                        supplier_id=supplier.id,
                        bid_price=participant_data.get('bid_price'),
                        is_winner=participant_data.get('is_winner', False),
                        rank=participant_data.get('rank'),
                        rejected=participant_data.get('rejected', False),
                        rejection_reason=participant_data.get('rejection_reason')
                    )
                    session.add(participation)
            
            # Обновляем participants_count
            lot.participants_count = len(protocol_data['participants'])
            
            session.commit()
            logger.info(f"Протокол {reg_number} сохранён: {len(protocol_data['participants'])} участников")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении протокола {protocol_data['reg_number']}: {e}")
            session.rollback()
            return False


def fetch_protocols_for_lots(session: Session, limit: int = 100) -> Dict:
    """
    Получает протоколы для лотов без final_price.
    
    Args:
        session: SQLAlchemy сессия
        limit: максимальное количество лотов для обработки
    
    Returns:
        Статистика: {'processed': int, 'success': int, 'failed': int}
    """
    scraper = ProtocolScraper()
    stats = {'processed': 0, 'success': 0, 'failed': 0}
    
    # Получаем лоты со статусом "Завершено" без final_price
    lots = session.query(Lot).filter(
        Lot.status.in_(['Завершено', 'Работа комиссии']),
        Lot.final_price.is_(None)
    ).limit(limit).all()
    
    logger.info(f"Найдено {len(lots)} лотов для получения протоколов")
    
    for lot in lots:
        protocol_data = scraper.fetch_protocol(lot.reg_number)
        
        if protocol_data and protocol_data.get('participants'):
            if scraper.save_protocol_data(session, protocol_data):
                stats['success'] += 1
            else:
                stats['failed'] += 1
        else:
            stats['failed'] += 1
        
        stats['processed'] += 1
        
        if stats['processed'] % 10 == 0:
            logger.info(f"Обработано {stats['processed']}/{len(lots)} лотов")
    
    logger.info(f"Завершено: processed={stats['processed']}, success={stats['success']}, failed={stats['failed']}")
    
    return stats


if __name__ == "__main__":
    # Тестирование
    from db.connection import get_session
    
    with get_session() as session:
        # Получаем протоколы для первых 10 лотов
        stats = fetch_protocols_for_lots(session, limit=10)
        
        print(f"\nСтатистика:")
        print(f"  Обработано: {stats['processed']}")
        print(f"  Успешно: {stats['success']}")
        print(f"  Ошибок: {stats['failed']}")
