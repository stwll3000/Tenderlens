"""
Скрипт для валидации и анализа собранных данных
"""

import pandas as pd
import json
import glob
from pathlib import Path

def load_latest_data() -> pd.DataFrame:
    """Загрузить последний файл с данными"""
    data_files = glob.glob('data/lots_all_*.json')
    
    if not data_files:
        raise FileNotFoundError("Не найдено файлов с данными")
    
    # Берем последний файл
    latest_file = sorted(data_files)[-1]
    print(f"Загружаем данные из: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    return df

def validate_data(df: pd.DataFrame):
    """Валидация и анализ данных"""
    print("\n" + "=" * 80)
    print("ВАЛИДАЦИЯ ДАННЫХ")
    print("=" * 80)
    
    # Базовая информация
    print(f"\n1. ОБЩАЯ ИНФОРМАЦИЯ")
    print(f"   Всего записей: {len(df)}")
    print(f"   Количество колонок: {len(df.columns)}")
    print(f"   Колонки: {', '.join(df.columns.tolist())}")
    
    # Информация о типах данных
    print(f"\n2. ТИПЫ ДАННЫХ")
    print(df.dtypes)
    
    # Пропущенные значения
    print(f"\n3. ПРОПУЩЕННЫЕ ЗНАЧЕНИЯ")
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_df = pd.DataFrame({
        'Пропусков': missing,
        'Процент': missing_pct
    })
    print(missing_df[missing_df['Пропусков'] > 0])
    
    # Статистика по числовым полям
    print(f"\n4. СТАТИСТИКА ПО НАЧАЛЬНОЙ ЦЕНЕ")
    if 'initial_price' in df.columns:
        price_stats = df['initial_price'].describe()
        print(price_stats)
        print(f"\n   Лотов с ценой: {df['initial_price'].notna().sum()}")
        print(f"   Лотов без цены: {df['initial_price'].isna().sum()}")
    
    # Распределение по регионам
    print(f"\n5. РАСПРЕДЕЛЕНИЕ ПО РЕГИОНАМ")
    if 'region_name' in df.columns:
        region_counts = df['region_name'].value_counts()
        print(region_counts)
    
    # Распределение по законам
    print(f"\n6. РАСПРЕДЕЛЕНИЕ ПО ЗАКОНАМ (44-ФЗ / 223-ФЗ)")
    if 'law' in df.columns:
        law_counts = df['law'].value_counts()
        print(law_counts)
    
    # Распределение по статусам
    print(f"\n7. РАСПРЕДЕЛЕНИЕ ПО СТАТУСАМ")
    if 'status' in df.columns:
        status_counts = df['status'].value_counts()
        print(status_counts)
    
    # Способы определения поставщика
    print(f"\n8. СПОСОБЫ ОПРЕДЕЛЕНИЯ ПОСТАВЩИКА (ТОП-5)")
    if 'purchase_method' in df.columns:
        method_counts = df['purchase_method'].value_counts().head(5)
        print(method_counts)
    
    # Примеры данных
    print(f"\n9. ПРИМЕРЫ ДАННЫХ (первые 3 записи)")
    print("\n" + "-" * 80)
    for idx, row in df.head(3).iterrows():
        print(f"\nЗапись #{idx + 1}:")
        print(f"  Номер: {row.get('reg_number', 'N/A')}")
        print(f"  Объект: {row.get('object_name', 'N/A')[:80]}...")
        print(f"  Заказчик: {row.get('customer_name', 'N/A')[:60]}...")
        print(f"  Цена: {row.get('initial_price', 'N/A')}")
        print(f"  Регион: {row.get('region_name', 'N/A')}")
        print(f"  Закон: {row.get('law', 'N/A')}")
        print(f"  Статус: {row.get('status', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("ВАЛИДАЦИЯ ЗАВЕРШЕНА")
    print("=" * 80)
    
    return df

def save_summary(df: pd.DataFrame):
    """Сохранить сводку в CSV"""
    output_file = 'data/lots_summary.csv'
    
    # Выбираем ключевые колонки
    columns_to_save = [
        'reg_number', 'object_name', 'customer_name', 'initial_price',
        'region_name', 'law', 'status', 'published_date', 'url'
    ]
    
    # Фильтруем только существующие колонки
    available_columns = [col for col in columns_to_save if col in df.columns]
    
    df[available_columns].to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nСводка сохранена в: {output_file}")

def main():
    """Основная функция"""
    try:
        # Загружаем данные
        df = load_latest_data()
        
        # Валидируем
        df = validate_data(df)
        
        # Сохраняем сводку
        save_summary(df)
        
        print("\n✅ Все проверки пройдены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
