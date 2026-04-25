"""
Тестовый скрипт для проверки извлечения данных со страницы деталей закупки.
"""

import requests
from bs4 import BeautifulSoup
import json

# Тестовый URL
test_url = "https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber=0338300031326000003"

print(f"Загрузка страницы: {test_url}\n")

# Загружаем страницу
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

response = session.get(test_url, timeout=30)
soup = BeautifulSoup(response.content, 'html.parser')

print("="*60)
print("ПОИСК ДАТ")
print("="*60)

# Ищем все элементы с датами
date_patterns = ['Размещено', 'Обновлено', 'Окончание подачи', 'подачи заявок']

for pattern in date_patterns:
    print(f"\nПоиск: '{pattern}'")
    # Ищем по тексту
    elements = soup.find_all(string=lambda text: text and pattern.lower() in text.lower())
    for elem in elements[:3]:  # Первые 3 совпадения
        print(f"  Найдено: {elem.strip()[:100]}")
        # Ищем родительский элемент
        parent = elem.parent
        if parent:
            print(f"  Родитель: {parent.name}, class={parent.get('class')}")
            # Ищем значение рядом
            next_sibling = parent.find_next_sibling()
            if next_sibling:
                print(f"  Значение: {next_sibling.get_text(strip=True)[:100]}")

print("\n" + "="*60)
print("ПОИСК ОКПД2")
print("="*60)

# Ищем таблицы
tables = soup.find_all('table')
print(f"\nНайдено таблиц: {len(tables)}")

for i, table in enumerate(tables[:5], 1):
    print(f"\nТаблица {i}:")
    rows = table.find_all('tr')[:3]  # Первые 3 строки
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if cells:
            row_text = ' | '.join(cell.get_text(strip=True)[:50] for cell in cells)
            print(f"  {row_text}")

print("\n" + "="*60)
print("СТРУКТУРА СТРАНИЦЫ")
print("="*60)

# Ищем основные контейнеры
containers = soup.find_all(['div', 'section'], class_=True)
print(f"\nНайдено контейнеров с классами: {len(containers)}")

# Показываем уникальные классы
classes = set()
for container in containers:
    class_list = container.get('class', [])
    if class_list:
        classes.add(class_list[0])

print("\nТоп-20 классов:")
for cls in sorted(classes)[:20]:
    print(f"  - {cls}")

# Сохраняем HTML для анализа
with open('data/test_page.html', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())

print(f"\nHTML сохранён в: data/test_page.html")
