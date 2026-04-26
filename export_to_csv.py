"""
Экспорт данных в CSV для ручной загрузки в Supabase.
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

def export_lots_to_csv(lots, output_file):
    """Экспорт лотов в CSV."""
    print(f"\nЭкспорт лотов в {output_file.name}...")
    
    # Поля для экспорта (соответствуют структуре таблицы lots)
    fieldnames = [
        'reg_number', 'url', 'law', 'purchase_method', 'status', 'object_name',
        'customer_name', 'customer_url', 'initial_price', 'final_price',
        'price_reduction_pct', 'region_code', 'region_name',
        'published_date', 'updated_date', 'deadline_date',
        'okpd2_codes', 'participants_count', 'scraped_at'
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
                'final_price': lot.get('final_price', ''),
                'price_reduction_pct': lot.get('price_reduction_pct', ''),
                'region_code': lot.get('region_code', ''),
                'region_name': lot.get('region_name', ''),
                'published_date': lot.get('published_date', ''),
                'updated_date': lot.get('updated_date', ''),
                'deadline_date': lot.get('deadline_date', ''),
                'okpd2_codes': json.dumps(lot.get('okpd2_codes')) if lot.get('okpd2_codes') else '',
                'participants_count': lot.get('participants_count', ''),
                'scraped_at': lot.get('scraped_at', datetime.now().isoformat())
            }
            writer.writerow(row)
    
    print(f"✓ Экспортировано {len(lots)} записей")

def export_customers_to_csv(lots, output_file):
    """Экспорт уникальных заказчиков в CSV."""
    print(f"\nЭкспорт заказчиков в {output_file.name}...")
    
    # Собираем уникальных заказчиков
    customers = {}
    for lot in lots:
        url = lot.get('customer_url')
        if url and url not in customers:
            customers[url] = {
                'name': lot.get('customer_name', ''),
                'url': url,
                'inn': '',  # Нет в данных
                'kpp': ''   # Нет в данных
            }
    
    fieldnames = ['name', 'url', 'inn', 'kpp']
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for customer in customers.values():
            writer.writerow(customer)
    
    print(f"✓ Экспортировано {len(customers)} уникальных заказчиков")

def export_regions_to_csv(lots, output_file):
    """Экспорт уникальных регионов в CSV."""
    print(f"\nЭкспорт регионов в {output_file.name}...")
    
    # Собираем уникальные регионы
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
    print("ЭКСПОРТ ДАННЫХ В CSV ДЛЯ SUPABASE")
    print("=" * 70)
    print()
    
    # Создаем директорию для экспорта
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Проверка файла
    if not DATA_FILE.exists():
        print(f"✗ Файл не найден: {DATA_FILE}")
        return
    
    # Загрузка данных
    lots = load_json_data(DATA_FILE)
    print()
    
    # Экспорт в CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Регионы (маленький файл)
    regions_file = OUTPUT_DIR / f"regions_{timestamp}.csv"
    export_regions_to_csv(lots, regions_file)
    
    # 2. Заказчики (средний файл)
    customers_file = OUTPUT_DIR / f"customers_{timestamp}.csv"
    export_customers_to_csv(lots, customers_file)
    
    # 3. Лоты (большой файл)
    lots_file = OUTPUT_DIR / f"lots_{timestamp}.csv"
    export_lots_to_csv(lots, lots_file)
    
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
    print("ИНСТРУКЦИЯ ПО ЗАГРУЗКЕ В SUPABASE:")
    print("1. Откройте https://supabase.com/dashboard")
    print("2. Выберите проект 'dnpjcxjjavzjmtfzlrip'")
    print("3. Перейдите в Table Editor")
    print("4. Загрузите файлы в следующем порядке:")
    print("   a) regions (сначала)")
    print("   b) customers (потом)")
    print("   c) lots (в конце)")
    print("5. Используйте опцию 'Import data from CSV'")
    print()
    print("✓ Экспорт завершен!")

if __name__ == "__main__":
    main()
