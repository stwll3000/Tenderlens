"""
Модуль для маппинга ОКПД2 кодов в нормализованные ниши.

Функции:
- map_okpd2_to_niche: определение ниши по ОКПД2 коду
- get_niche_name: получение человекочитаемого названия ниши
- init_niche_categories: инициализация справочника категорий в БД
"""

import json
from typing import Optional, List
from sqlalchemy.orm import Session
from db.models import LotCategory


# Справочник ниш: ОКПД2 префиксы → niche_slug
NICHE_MAP = {
    "med-rashodniki": {
        "name": "Медицинские расходники",
        "okpd2_prefixes": ["32.50.13", "32.50.21", "32.50.41", "32.50.50"]
    },
    "it-oborudovanie": {
        "name": "IT оборудование",
        "okpd2_prefixes": ["26.20", "26.30", "27.20", "26.40"]
    },
    "siz": {
        "name": "Средства индивидуальной защиты",
        "okpd2_prefixes": ["14.12", "32.99.11", "13.92"]
    },
    "kanc": {
        "name": "Канцелярские товары",
        "okpd2_prefixes": ["17.23", "32.99.12", "17.12"]
    },
    "klining-uslugi": {
        "name": "Клининговые услуги",
        "okpd2_prefixes": ["81.21", "81.22", "81.29"]
    },
    "mebel": {
        "name": "Мебель",
        "okpd2_prefixes": ["31.01", "31.02", "31.03", "31.09"]
    },
    "stroymaterialy": {
        "name": "Строительные материалы",
        "okpd2_prefixes": ["23.3", "23.4", "23.5", "23.6", "23.7"]
    },
    "produkty": {
        "name": "Продукты питания",
        "okpd2_prefixes": ["10.1", "10.2", "10.3", "10.4", "10.5", "10.6", "10.7", "10.8", "10.9"]
    },
    "med-oborudovanie": {
        "name": "Медицинское оборудование",
        "okpd2_prefixes": ["26.60", "32.50.1", "32.50.2"]
    },
    "lekarstva": {
        "name": "Лекарственные препараты",
        "okpd2_prefixes": ["21.1", "21.2"]
    },
    "transport": {
        "name": "Транспортные средства",
        "okpd2_prefixes": ["29.1", "29.2", "29.3"]
    },
    "remont-stroitelstvo": {
        "name": "Ремонт и строительство",
        "okpd2_prefixes": ["41.", "42.", "43."]
    },
    "ohrana": {
        "name": "Охранные услуги",
        "okpd2_prefixes": ["80.1", "80.2"]
    },
    "it-uslugi": {
        "name": "IT услуги",
        "okpd2_prefixes": ["62.", "63.1"]
    },
    "obrazovanie": {
        "name": "Образовательные услуги",
        "okpd2_prefixes": ["85.1", "85.2", "85.3", "85.4"]
    },
}


def map_okpd2_to_niche(okpd2_codes: Optional[str]) -> Optional[str]:
    """
    Определяет niche_slug по ОКПД2 кодам лота.
    
    Args:
        okpd2_codes: JSON-строка с массивом ОКПД2 кодов
    
    Returns:
        niche_slug или None, если ниша не определена
    
    Example:
        >>> map_okpd2_to_niche('["32.50.13.110", "32.50.21.000"]')
        'med-rashodniki'
    """
    if not okpd2_codes:
        return None
    
    try:
        codes = json.loads(okpd2_codes) if isinstance(okpd2_codes, str) else okpd2_codes
    except (json.JSONDecodeError, TypeError):
        return None
    
    if not codes or not isinstance(codes, list):
        return None
    
    # Проходим по всем кодам и ищем совпадение с префиксами
    for code in codes:
        if not isinstance(code, str):
            continue
        
        code = code.strip()
        
        # Проверяем каждую нишу
        for niche_slug, niche_data in NICHE_MAP.items():
            for prefix in niche_data["okpd2_prefixes"]:
                if code.startswith(prefix):
                    return niche_slug
    
    return None


def get_niche_name(niche_slug: str) -> Optional[str]:
    """
    Получает человекочитаемое название ниши.
    
    Args:
        niche_slug: идентификатор ниши
    
    Returns:
        Название ниши или None
    
    Example:
        >>> get_niche_name('med-rashodniki')
        'Медицинские расходники'
    """
    niche_data = NICHE_MAP.get(niche_slug)
    return niche_data["name"] if niche_data else None


def get_all_niches() -> List[dict]:
    """
    Возвращает список всех ниш с их данными.
    
    Returns:
        Список словарей с информацией о нишах
    """
    return [
        {
            "slug": slug,
            "name": data["name"],
            "okpd2_prefixes": data["okpd2_prefixes"]
        }
        for slug, data in NICHE_MAP.items()
    ]


def init_niche_categories(session: Session) -> int:
    """
    Инициализирует таблицу lot_categories справочными данными.
    
    Args:
        session: SQLAlchemy сессия
    
    Returns:
        Количество добавленных записей
    """
    count = 0
    
    for niche_slug, niche_data in NICHE_MAP.items():
        for okpd2_prefix in niche_data["okpd2_prefixes"]:
            # Проверяем, существует ли уже такая запись
            existing = session.query(LotCategory).filter_by(
                okpd2_prefix=okpd2_prefix,
                niche_slug=niche_slug
            ).first()
            
            if not existing:
                category = LotCategory(
                    okpd2_prefix=okpd2_prefix,
                    niche_slug=niche_slug,
                    name=niche_data["name"]
                )
                session.add(category)
                count += 1
    
    session.commit()
    return count


def update_lot_niches(session: Session, batch_size: int = 1000) -> int:
    """
    Обновляет niche_slug для всех лотов в БД на основе их ОКПД2 кодов.
    
    Args:
        session: SQLAlchemy сессия
        batch_size: размер батча для обработки
    
    Returns:
        Количество обновленных лотов
    """
    from db.models import Lot
    
    updated_count = 0
    offset = 0
    
    while True:
        # Получаем батч лотов без niche_slug
        lots = session.query(Lot).filter(
            Lot.niche_slug.is_(None),
            Lot.okpd2_codes.isnot(None)
        ).limit(batch_size).offset(offset).all()
        
        if not lots:
            break
        
        for lot in lots:
            niche = map_okpd2_to_niche(lot.okpd2_codes)
            if niche:
                lot.niche_slug = niche
                updated_count += 1
        
        session.commit()
        offset += batch_size
    
    return updated_count


if __name__ == "__main__":
    # Тестирование
    test_codes = '["32.50.13.110", "32.50.21.000"]'
    niche = map_okpd2_to_niche(test_codes)
    print(f"ОКПД2: {test_codes}")
    print(f"Ниша: {niche}")
    print(f"Название: {get_niche_name(niche)}")
    
    print("\nВсе ниши:")
    for n in get_all_niches():
        print(f"  {n['slug']}: {n['name']} ({len(n['okpd2_prefixes'])} кодов)")
