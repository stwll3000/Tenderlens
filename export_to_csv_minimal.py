"""
Экспорт данных в CSV с минимальным набором полей для Supabase.
"""

import json
import csv
import sys
import io
from pathlib import Path
from datetime import datetime

# Настройка вывода для Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Путь к данным
DATA_FILE = Path("data/lots_multi_regions_6000_20260425.json")
OUTPUT_DIR = Path("data/csv_export")

def load_json_data(file_path):
    """Загрузка данных из JSON файла."""
    print(f"Загрузка данных из {file_path.name}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"✓ Загружено {len(data)} записей")
    return data

def export_lots_minimal(lots, output_file):
    """Экспорт лотов с минимальным набором полей."""
    print(f"\nЭкспорт лотов (минимальные поля) в {output_file.name}...")
    
    # Минимальный набор полей
    fieldnames = [
        'reg_number', 'url', 'law', 'purchase_method', 'status', 'object_name',
        'customer_name', 'customer_url', 'initial_price', 
        'region_code', 'region_name', 'scraped_at'
    ]
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for lot in lots:
            row = {
                'reg_number': lot.get('reg_number', ''),
                'url': lot.get('url', ''),
                'law': lot.get('law', '44-ФЗ'),
                'purchase_method': lot.get('purchase_method', ''),
                'status': lot.get('status', ''),
                'object_name': lot.get('object_name', ''),
                'customer_name': lot.get('customer_name', ''),
                'customer_url': lot.get('customer_url', ''),
                'initial_price': lot.get('initial_price', 0.0),
                'region_code': lot.get('region_code', ''),
                'region_name': lot.get('region_name', ''),
                'scraped_at': lot.get('scraped_at', datetime.now().isoformat())
            }
            writer.writerow(row)
    
    print(f"✓ Экспортировано {len(lots)} записей")

def export_customers_minimal(lots, output_file):
    """Экспорт уникальных заказчиков."""
    print(f"\nЭкспорт заказчиков в {output_file.name}...")
    
    customers = {}
    for lot in lots:
        url = lot.get('customer_url')
        if url and url not in customers:
            customers[url] = {
                'name': lot.get('customer_name', ''),
                'url': url
            }
    
    fieldnames = ['name', 'url']
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for customer in customers.values():
            writer.writerow(customer)
    
    print(f"✓ Экспортировано {len(customers)} уникальных заказчиков")

def export_regions_minimal(lots, output_file):
    """Экспорт уникальных регионов."""
    print(f"\nЭкспорт регионов в {output_file.name}...")
    
    regions = {}
    for lot in lots:
        code = lot.get('region_code')
        if code and code not in regions:
            regions[code] = {
                'code': code,
                'name': lot.get('region_name', '')
            }
    
    fieldnames = ['code', 'name']
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for region in sorted(regions.values(), key=lambda x: x['code']):
            writer.writerow(region)
    
    print(f"✓ Экспортировано {len(regions)} регионов")

def main():
    print("=" * 70)
    print("ЭКСПОРТ ДАННЫХ В CSV (МИНИМАЛЬНЫЕ ПОЛЯ)")
    print("=" * 70)
    print()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if not DATA_FILE.exists():
        print(f"✗ Файл не найден: {DATA_FILE}")
        return
    
    lots = load_json_data(DATA_FILE)
    print()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Экспорт с минимальными полями
    regions_file = OUTPUT_DIR / f"regions_minimal_{timestamp}.csv"
    export_regions_minimal(lots, regions_file)
    
    customers_file = OUTPUT_DIR / f"customers_minimal_{timestamp}.csv"
    export_customers_minimal(lots, customers_file)
    
    lots_file = OUTPUT_DIR / f"lots_minimal_{timestamp}.csv"
    export_lots_minimal(lots, lots_file)
    
    print()
    print("=" * 70)
    print("РЕЗУЛЬТАТ")
    print("=" * 70)
    print(f"Файлы сохранены в: {OUTPUT_DIR.absolute()}")
    print()
    print("Файлы для загрузки:")
    print(f"  1. {regions_file.name}")
    print(f"  2. {customers_file.name}")
    print(f"  3. {lots_file.name}")
    print()
    print("✓ Экспорт завершен!")

if __name__ == "__main__":
    main()
