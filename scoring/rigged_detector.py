"""
Детектор "заточки" тендера под конкретного поставщика.

Анализирует текст ТЗ и название объекта закупки на предмет признаков,
которые указывают на то, что тендер заточен под конкретного поставщика.

Признаки заточки:
- Требование редкого опыта (>5 лет в узкой нише)
- Требование редких СРО
- Указание конкретных моделей/производителей
- Запрет эквивалентов
- Географическая привязка
- Нереальные сроки
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class RiggedSignal:
    """Сигнал о заточке."""
    pattern: str
    flag: str
    description: str
    severity: int  # 1-3 (1=слабый, 3=сильный)


# Паттерны для детектирования заточки
RIGGED_PATTERNS = [
    RiggedSignal(
        pattern=r"опыт.*не\s*менее\s*([5-9]|1[0-9])\s*(лет|года)",
        flag="long_experience_required",
        description="Требование большого опыта работы",
        severity=2
    ),
    RiggedSignal(
        pattern=r"наличи[ея]\s*св-?ва?\s*СРО",
        flag="rare_sro",
        description="Требование СРО",
        severity=2
    ),
    RiggedSignal(
        pattern=r"конкретн[аы][ея]?\s*модел[ьи]",
        flag="specific_model",
        description="Указание конкретной модели",
        severity=3
    ),
    RiggedSignal(
        pattern=r"производител[ья]\s*[A-ZА-Я][\w-]+",
        flag="specific_manufacturer",
        description="Указание конкретного производителя",
        severity=3
    ),
    RiggedSignal(
        pattern=r"эквивалент\s*не\s*допуск",
        flag="no_equivalent",
        description="Запрет эквивалентов",
        severity=3
    ),
    RiggedSignal(
        pattern=r"должен\s*находиться\s*в\s*([\w\s-]+)\s*(области|крае|округе)",
        flag="geo_lock",
        description="Географическая привязка поставщика",
        severity=2
    ),
    RiggedSignal(
        pattern=r"исключительн[ыо][ея]?\s*прав[оа]",
        flag="exclusive_rights",
        description="Требование исключительных прав",
        severity=3
    ),
    RiggedSignal(
        pattern=r"сертификат\s*(?:от|выданный)\s*[A-ZА-Я][\w\s-]+",
        flag="specific_certificate",
        description="Требование сертификата от конкретной организации",
        severity=2
    ),
    RiggedSignal(
        pattern=r"опыт\s*работы\s*с\s*[A-ZА-Я][\w\s-]+",
        flag="specific_client_experience",
        description="Требование опыта работы с конкретным клиентом",
        severity=3
    ),
    RiggedSignal(
        pattern=r"(?:поставка|выполнение)\s*в\s*течени[ие]\s*([1-3])\s*(?:дн|сут)",
        flag="unrealistic_deadline",
        description="Нереально короткие сроки поставки",
        severity=2
    ),
]


def detect_rigged_signals(
    object_name: str,
    tz_text: str = None
) -> Tuple[List[str], int, Dict]:
    """
    Детектирует признаки заточки в тексте.
    
    Args:
        object_name: название объекта закупки
        tz_text: полный текст ТЗ
    
    Returns:
        (flags, total_severity, details) где:
        - flags: список флагов
        - total_severity: суммарная серьезность (0-30)
        - details: детали найденных паттернов
    """
    text = (object_name + "\n" + (tz_text or "")).lower()
    
    flags = []
    total_severity = 0
    details = []
    
    for signal in RIGGED_PATTERNS:
        matches = re.findall(signal.pattern, text, re.IGNORECASE)
        
        if matches:
            flags.append(signal.flag)
            total_severity += signal.severity
            
            details.append({
                "flag": signal.flag,
                "description": signal.description,
                "severity": signal.severity,
                "matches": matches[:3]  # первые 3 совпадения
            })
    
    return flags, total_severity, details


def calculate_rigged_score(flags: List[str], total_severity: int) -> float:
    """
    Рассчитывает score "чистоты" тендера (0-1).
    
    Args:
        flags: список флагов заточки
        total_severity: суммарная серьезность
    
    Returns:
        Score от 0 (явная заточка) до 1 (чистый тендер)
    """
    if not flags:
        return 0.95
    
    # Базовый штраф за количество флагов
    penalty = len(flags) * 0.15
    
    # Дополнительный штраф за серьезность
    severity_penalty = min(total_severity / 30, 0.5)
    
    score = 1.0 - penalty - severity_penalty
    
    return max(0.0, min(1.0, score))


def analyze_lot_rigging(
    object_name: str,
    tz_text: str = None
) -> Dict:
    """
    Полный анализ лота на предмет заточки.
    
    Args:
        object_name: название объекта закупки
        tz_text: полный текст ТЗ
    
    Returns:
        Словарь с результатами анализа
    """
    flags, total_severity, details = detect_rigged_signals(object_name, tz_text)
    score = calculate_rigged_score(flags, total_severity)
    
    # Определяем уровень риска
    if score >= 0.8:
        risk_level = "Низкий"
        recommendation = "Тендер выглядит чистым, можно участвовать"
    elif score >= 0.5:
        risk_level = "Средний"
        recommendation = "Есть признаки заточки, требуется детальный анализ"
    else:
        risk_level = "Высокий"
        recommendation = "Высокая вероятность заточки, участие не рекомендуется"
    
    return {
        "purity_score": round(score, 2),
        "risk_level": risk_level,
        "recommendation": recommendation,
        "flags": flags,
        "total_severity": total_severity,
        "signals_found": len(flags),
        "details": details,
    }


def batch_analyze_lots(lots: List[Dict]) -> List[Dict]:
    """
    Анализирует множество лотов на заточку.
    
    Args:
        lots: список словарей с полями 'object_name' и 'tz_text'
    
    Returns:
        Список результатов анализа
    """
    results = []
    
    for lot in lots:
        analysis = analyze_lot_rigging(
            lot.get('object_name', ''),
            lot.get('tz_text')
        )
        
        results.append({
            'lot_id': lot.get('id'),
            'reg_number': lot.get('reg_number'),
            **analysis
        })
    
    return results


if __name__ == "__main__":
    # Тестирование
    
    # Пример 1: Чистый тендер
    clean_lot = """
    Поставка медицинских расходных материалов для нужд больницы.
    Требования: соответствие ГОСТ, сертификат качества.
    """
    
    result1 = analyze_lot_rigging("Медицинские расходники", clean_lot)
    print("Пример 1 (чистый тендер):")
    print(f"  Score: {result1['purity_score']}")
    print(f"  Риск: {result1['risk_level']}")
    print(f"  Рекомендация: {result1['recommendation']}")
    print()
    
    # Пример 2: Заточенный тендер
    rigged_lot = """
    Поставка медицинского оборудования производителя Siemens, модель ACUSON S2000.
    Эквиваленты не допускаются. Требуется опыт работы не менее 7 лет в данной сфере.
    Поставщик должен находиться в Московской области.
    Срок поставки - 2 дня с момента заключения контракта.
    """
    
    result2 = analyze_lot_rigging("Медицинское оборудование Siemens", rigged_lot)
    print("Пример 2 (заточенный тендер):")
    print(f"  Score: {result2['purity_score']}")
    print(f"  Риск: {result2['risk_level']}")
    print(f"  Рекомендация: {result2['recommendation']}")
    print(f"  Найдено сигналов: {result2['signals_found']}")
    print(f"  Флаги: {', '.join(result2['flags'])}")
    print("\n  Детали:")
    for detail in result2['details']:
        print(f"    - {detail['description']} (severity: {detail['severity']})")
