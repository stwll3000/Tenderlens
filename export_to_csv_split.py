"""
Экспорт данных в CSV с разбивкой на части по 900 записей.
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

def export_lots_batch(lots, output_file, fieldnames):
    """Экспорт батча лотов в CSV."""
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

def split_and_export_lots(lots, batch_size=900):
    """Разбивка лотов на части и экспорт."""
    print(f"\nРазбивка {len(lots)} лотов на части по {batch_size}...")
    print()
    
    fieldnames = [
        'reg_number', 'url', 'law', 'purchase_method', 'status', 'object_name',
        'customer_name', 'customer_url', 'initial_price', 
        'region_code', 'region_name', 'scraped_at'
    ]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    total_batches = (len(lots) + batch_size - 1) // batch_size
    
    files_created = []
    
    for i in range(0, len(lots), batch_size):
        batch_num = i // batch_size + 1
        batch = lots[i:i + batch_size]
        
        output_file = OUTPUT_DIR / f"lots_part{batch_num}_{timestamp}.csv"
        export_lots_batch(batch, output_file, fieldnames)
        
        files_created.append(output_file.name)
        print(f"  ✓ Часть {batch_num}/{total_batches}: {output_file.name} ({len(batch)} записей)")
    
    return files_created

def export_customers_minimal(lots, output_file):
    """Экспорт уникальных заказчиков."""
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
    
    return len(customers)

def export_regions_minimal(lots, output_file):
    """Экспорт уникальных регионов."""
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
    
    return len(regions)

def main():
    print("=" * 70)
    print("ЭКСПОРТ ДАННЫХ В CSV (РАЗБИВКА НА ЧАСТИ)")
    print("=" * 70)
    print()
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if not DATA_FILE.exists():
        print(f"✗ Файл не найден: {DATA_FILE}")
        return
    
    lots = load_json_data(DATA_FILE)
    print()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Экспорт регионов
    print("Экспорт регионов...")
    regions_file = OUTPUT_DIR / f"regions_{timestamp}.csv"
    regions_count = export_regions_minimal(lots, regions_file)
    print(f"  ✓ {regions_file.name} ({regions_count} регионов)")
    print()
    
    # Экспорт заказчиков
    print("Экспорт заказчиков...")
    customers_file = OUTPUT_DIR / f"customers_{timestamp}.csv"
    customers_count = export_customers_minimal(lots, customers_file)
    print(f"  ✓ {customers_file.name} ({customers_count} заказчиков)")
    
    # Экспорт лотов по частям
    lots_files = split_and_export_lots(lots, batch_size=900)
    
    print()
    print("=" * 70)
    print("РЕЗУЛЬТАТ")
    print("=" * 70)
    print(f"Директория: {OUTPUT_DIR.absolute()}")
    print()
    print("ПОРЯДОК ЗАГРУЗКИ В SUPABASE:")
    print()
    print(f"1. {regions_file.name} → таблица 'regions'")
    print(f"2. {customers_file.name} → таблица 'customers'")
    print()
    print("3. Лоты (загружайте по порядку в таблицу 'lots'):")
    for i, filename in enumerate(lots_files, 1):
        print(f"   {i}. {filename}")
    print()
    print("✓ Экспорт завершен!")

if __name__ == "__main__":
    main()
