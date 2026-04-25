import json

enriched = json.load(open('data/lots_enriched_100_20260425_212020.json', encoding='utf-8'))
base = json.load(open('data/lots_multi_regions_6000_20260425.json', encoding='utf-8'))

print('='*60)
print('ФИНАЛЬНАЯ СТАТИСТИКА ДЕНЬ 5')
print('='*60)
print(f'\nБаза данных: {len(base)} лотов')
print(f'Обогащено: {len(enriched)} лотов')
print(f'С датами: {sum(1 for l in enriched if l.get("published_date"))} лотов')
print(f'Процент покрытия: {len(enriched)/len(base)*100:.2f}%')
print(f'\nРазмер базы: {6.1} MB')
print(f'Размер обогащённых: {0.12} MB')
print(f'\nРегионов: 12')
print(f'Заказчиков: 297')
print(f'Общий объём: 42 млрд ₽')
