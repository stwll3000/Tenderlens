"""
Скрипт для объединения старых и новых данных
"""
import json
from datetime import datetime

# Загружаем старые данные
with open('data/lots_all_20260425_185919.json', 'r', encoding='utf-8') as f:
    old_data = json.load(f)

# Загружаем новые данные
with open('data/lots_54_20260425_190912.json', 'r', encoding='utf-8') as f:
    new_data = json.load(f)

# Объединяем
all_data = old_data + new_data

print(f'Старые данные: {len(old_data)} лотов')
print(f'Новые данные: {len(new_data)} лотов')
print(f'Всего: {len(all_data)} лотов')

# Проверяем уникальность по reg_number
unique_numbers = set(lot['reg_number'] for lot in all_data)
print(f'Уникальных лотов: {len(unique_numbers)}')

if len(unique_numbers) < len(all_data):
    print(f'Найдено дубликатов: {len(all_data) - len(unique_numbers)}')
    # Удаляем дубликаты
    seen = set()
    unique_data = []
    for lot in all_data:
        if lot['reg_number'] not in seen:
            seen.add(lot['reg_number'])
            unique_data.append(lot)
    all_data = unique_data
    print(f'После удаления дубликатов: {len(all_data)} лотов')

# Сохраняем
filename = f'data/lots_all_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f'\nСохранено в: {filename}')
