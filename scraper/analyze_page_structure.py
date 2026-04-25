"""
Скрипт для анализа структуры страницы закупки на zakupki.gov.ru
Помогает найти правильные селекторы для парсинга дополнительных полей.
"""

import requests
from bs4 import BeautifulSoup
import json

# Берём URL из существующих данных
test_url = "https://zakupki.gov.ru/epz/order/notice/zk20/view/common-info.html?regNumber=0851600011226000009"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

print(f"Fetching: {test_url}\n")

try:
    response = requests.get(test_url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'lxml')
    
    # Ищем все блоки с данными
    print("=== Searching for date fields ===\n")
    
    # Вариант 1: таблицы с информацией
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables\n")
    
    for i, table in enumerate(tables[:3]):  # первые 3 таблицы
        print(f"--- Table {i+1} ---")
        rows = table.find_all('tr')
        for row in rows[:5]:  # первые 5 строк
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if any(keyword in label.lower() for keyword in ['дата', 'размещ', 'окончан', 'подач']):
                    print(f"  {label}: {value}")
        print()
    
    # Вариант 2: div блоки
    print("\n=== Searching for OKPD2 codes ===\n")
    
    # Ищем упоминания ОКПД2
    okpd_elements = soup.find_all(string=lambda text: text and 'ОКПД2' in text)
    print(f"Found {len(okpd_elements)} mentions of OKPD2\n")
    
    for elem in okpd_elements[:3]:
        parent = elem.parent
        print(f"Element: {elem.strip()}")
        print(f"Parent tag: {parent.name}")
        print(f"Parent class: {parent.get('class', [])}")
        
        # Ищем соседние элементы
        next_sibling = parent.find_next_sibling()
        if next_sibling:
            print(f"Next sibling: {next_sibling.get_text(strip=True)[:100]}")
        print()
    
    # Вариант 3: ищем количество участников
    print("\n=== Searching for participants count ===\n")
    
    participant_keywords = ['участник', 'заявк', 'предложен']
    for keyword in participant_keywords:
        elements = soup.find_all(string=lambda text: text and keyword in text.lower())
        if elements:
            print(f"Keyword '{keyword}': found {len(elements)} matches")
            for elem in elements[:2]:
                print(f"  - {elem.strip()[:100]}")
    
    # Сохраняем HTML для детального анализа
    with open('scraper/page_sample.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    print("\n[SUCCESS] HTML saved to scraper/page_sample.html")
    print("You can open it in browser to inspect elements manually")
    
except Exception as e:
    print(f"[ERROR] {e}")
