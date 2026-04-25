"""
Улучшенный скрипт для извлечения дат и других полей со страницы закупки.
"""

import sys
import io
from bs4 import BeautifulSoup

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('scraper/page_sample.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'lxml')

print("=== Extracting dates ===\n")

# Ищем блоки с датами
date_titles = soup.find_all('span', class_='cardMainInfo__title')

for title in date_titles:
    title_text = title.get_text(strip=True)
    
    # Ищем соседний элемент с контентом
    content = title.find_next_sibling('span', class_='cardMainInfo__content')
    
    if content and any(kw in title_text for kw in ['Размещено', 'Обновлено', 'Окончание']):
        print(f"{title_text}: {content.get_text(strip=True)}")

print("\n=== Searching for OKPD2 ===\n")

# Ищем таблицы с позициями
tables = soup.find_all('table')
for i, table in enumerate(tables):
    # Ищем заголовки таблицы
    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    
    if any('ОКПД' in h or 'Код' in h for h in headers):
        print(f"Table {i+1} headers: {headers}")
        
        # Первая строка данных
        first_row = table.find('tbody').find('tr') if table.find('tbody') else None
        if first_row:
            cells = [td.get_text(strip=True) for td in first_row.find_all('td')]
            print(f"First row: {cells[:3]}")
        print()

print("\n=== Searching for participants ===\n")

# Ищем информацию об участниках
participant_keywords = ['Количество участников', 'Подано заявок', 'участник']

for keyword in participant_keywords:
    elements = soup.find_all(string=lambda t: t and keyword.lower() in t.lower())
    
    if elements:
        print(f"Keyword '{keyword}': {len(elements)} matches")
        for elem in elements[:2]:
            parent = elem.parent
            print(f"  Text: {elem.strip()[:80]}")
            print(f"  Parent: {parent.name}, class: {parent.get('class', [])}")
            
            # Ищем значение рядом
            next_elem = parent.find_next_sibling()
            if next_elem:
                print(f"  Value: {next_elem.get_text(strip=True)[:50]}")
        print()
