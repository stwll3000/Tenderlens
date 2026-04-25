"""
Анализ собранных данных по множеству регионов.
"""

import sys
import io
import json
import pandas as pd
from pathlib import Path

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Загрузка данных
data_file = Path('data/lots_multi_regions_6000_20260425.json')
with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

df = pd.DataFrame(data)
df['initial_price'] = pd.to_numeric(df['initial_price'], errors='coerce')

print("="*60)
print("СТАТИСТИКА СОБРАННЫХ ДАННЫХ")
print("="*60)
print(f"\nВсего лотов: {len(df):,}")
print(f"Регионов: {df['region_code'].nunique()}")
print(f"Заказчиков: {df['customer_name'].nunique():,}")

print("\n" + "="*60)
print("ПО РЕГИОНАМ:")
print("="*60)
region_stats = df.groupby('region_name').agg({
    'reg_number': 'count',
    'initial_price': 'sum'
}).round(0)
region_stats.columns = ['Лотов', 'Объём (₽)']
region_stats = region_stats.sort_values('Лотов', ascending=False)
print(region_stats)

print("\n" + "="*60)
print("ПО ЗАКОНАМ:")
print("="*60)
law_stats = df['law'].value_counts()
for law, count in law_stats.items():
    print(f"{law}: {count:,} ({count/len(df)*100:.1f}%)")

print("\n" + "="*60)
print("ФИНАНСЫ:")
print("="*60)
total_volume = df['initial_price'].sum()
avg_price = df['initial_price'].mean()
median_price = df['initial_price'].median()

print(f"Общий объём: {total_volume:,.0f} ₽")
print(f"Средняя цена: {avg_price:,.0f} ₽")
print(f"Медианная цена: {median_price:,.0f} ₽")

print("\n" + "="*60)
print("ТОП-10 ЗАКАЗЧИКОВ:")
print("="*60)
top_customers = df.groupby('customer_name').agg({
    'reg_number': 'count',
    'initial_price': 'sum'
}).sort_values('initial_price', ascending=False).head(10)
top_customers.columns = ['Лотов', 'Объём (₽)']
print(top_customers)

print("\n" + "="*60)
print("ФАЙЛ СОХРАНЁН:")
print("="*60)
print(f"Путь: {data_file}")
print(f"Размер: {data_file.stat().st_size / 1024 / 1024:.1f} MB")
