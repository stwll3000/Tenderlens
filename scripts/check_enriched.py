import json

data = json.load(open('data/lots_enriched_test_20260425_211924.json', encoding='utf-8'))

lot = data[0]
print('Номер:', lot['reg_number'])
print('Размещено:', lot['published_date'])
print('Дедлайн:', lot['deadline_date'])
print('ОКПД2:', lot['okpd2_codes'])

print('\nВсе 10 лотов:')
for l in data:
    print(f"  {l['reg_number']}: {l['published_date']} -> {l['deadline_date']}")
