import json
from datetime import datetime
from collections import Counter

# Загружаем обогащённые данные
data = json.load(open('data/lots_enriched_100_20260425_212020.json', encoding='utf-8'))

print("="*60)
print("АНАЛИЗ ОБОГАЩЁННЫХ ДАННЫХ")
print("="*60)

# Статистика по датам
with_dates = [lot for lot in data if lot.get('published_date')]
with_deadline = [lot for lot in data if lot.get('deadline_date')]
with_okpd2 = [lot for lot in data if lot.get('okpd2_codes')]

print(f"\nВсего лотов: {len(data)}")
print(f"С датой размещения: {len(with_dates)} ({len(with_dates)/len(data)*100:.1f}%)")
print(f"С дедлайном: {len(with_deadline)} ({len(with_deadline)/len(data)*100:.1f}%)")
print(f"С ОКПД2: {len(with_okpd2)} ({len(with_okpd2)/len(data)*100:.1f}%)")

# Анализ сроков подачи заявок
print("\n" + "="*60)
print("АНАЛИЗ СРОКОВ ПОДАЧИ ЗАЯВОК")
print("="*60)

deadlines = []
for lot in data:
    if lot.get('published_date') and lot.get('deadline_date'):
        try:
            pub = datetime.strptime(lot['published_date'], '%d.%m.%Y')
            dead = datetime.strptime(lot['deadline_date'], '%d.%m.%Y')
            days = (dead - pub).days
            if days >= 0:
                deadlines.append(days)
        except:
            pass

if deadlines:
    print(f"\nСредний срок подачи: {sum(deadlines)/len(deadlines):.1f} дней")
    print(f"Минимальный срок: {min(deadlines)} дней")
    print(f"Максимальный срок: {max(deadlines)} дней")
    
    # Распределение по срокам
    print("\nРаспределение по срокам:")
    ranges = [(0, 3), (4, 7), (8, 14), (15, 30), (31, 60)]
    for start, end in ranges:
        count = sum(1 for d in deadlines if start <= d <= end)
        print(f"  {start}-{end} дней: {count} лотов ({count/len(deadlines)*100:.1f}%)")

# Анализ дат размещения
print("\n" + "="*60)
print("АНАЛИЗ ДАТ РАЗМЕЩЕНИЯ")
print("="*60)

pub_dates = []
for lot in with_dates:
    try:
        pub = datetime.strptime(lot['published_date'], '%d.%m.%Y')
        pub_dates.append(pub)
    except:
        pass

if pub_dates:
    pub_dates.sort()
    print(f"\nПериод: {pub_dates[0].strftime('%d.%m.%Y')} - {pub_dates[-1].strftime('%d.%m.%Y')}")
    print(f"Дней в выборке: {(pub_dates[-1] - pub_dates[0]).days}")
    
    # По дням недели
    weekdays = Counter(d.strftime('%A') for d in pub_dates)
    print("\nПо дням недели:")
    days_ru = {
        'Monday': 'Понедельник',
        'Tuesday': 'Вторник', 
        'Wednesday': 'Среда',
        'Thursday': 'Четверг',
        'Friday': 'Пятница',
        'Saturday': 'Суббота',
        'Sunday': 'Воскресенье'
    }
    for day, count in weekdays.most_common():
        print(f"  {days_ru.get(day, day)}: {count} лотов")

# Примеры лотов
print("\n" + "="*60)
print("ПРИМЕРЫ ОБОГАЩЁННЫХ ЛОТОВ")
print("="*60)

for i, lot in enumerate(data[:3], 1):
    print(f"\n{i}. {lot['reg_number']}")
    print(f"   Размещено: {lot.get('published_date', 'N/A')}")
    print(f"   Дедлайн: {lot.get('deadline_date', 'N/A')}")
    print(f"   ОКПД2: {lot.get('okpd2_codes', [])}")
    print(f"   Цена: {lot['initial_price']:,.0f} ₽")
