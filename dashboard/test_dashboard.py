"""
Скрипт для быстрого тестирования дашборда.
Проверяет загрузку данных и импорт модулей.
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent))

import json
import pandas as pd
from analytics import pricing, competition

def test_dashboard():
    """Тестирование компонентов дашборда."""
    
    print("=== Testing TenderLens Dashboard ===\n")
    
    # 1. Проверка данных
    print("1. Checking data files...")
    data_dir = Path(__file__).parent.parent / "data"
    json_files = sorted(data_dir.glob("lots_all_*.json"), reverse=True)
    
    if not json_files:
        print("   [ERROR] Data files not found!")
        return False
    
    latest_file = json_files[0]
    print(f"   [OK] Found file: {latest_file.name}")
    
    # 2. Загрузка данных
    print("\n2. Loading data...")
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    df['initial_price'] = pd.to_numeric(df['initial_price'], errors='coerce')
    
    print(f"   [OK] Loaded {len(df)} lots")
    print(f"   [OK] Regions: {df['region_name'].nunique()}")
    print(f"   [OK] Customers: {df['customer_name'].nunique()}")
    
    # 3. Тестирование модулей аналитики
    print("\n3. Testing analytics modules...")
    
    try:
        price_dist = pricing.analyze_price_distribution(df)
        print(f"   [OK] pricing.analyze_price_distribution() works")
        print(f"        Average price: {price_dist['mean']:,.0f} RUB")
        
        top_cust = competition.top_customers(df, n=5)
        print(f"   [OK] competition.top_customers() works")
        print(f"        Top customer: {top_cust.index[0]}")
        
        hhi = competition.market_concentration(df)
        print(f"   [OK] competition.market_concentration() works")
        print(f"        HHI: {hhi['hhi']:.0f}")
        
    except Exception as e:
        print(f"   [ERROR] Analytics modules error: {e}")
        return False
    
    # 4. Проверка Streamlit
    print("\n4. Checking Streamlit...")
    try:
        import streamlit
        print(f"   [OK] Streamlit installed (version {streamlit.__version__})")
    except ImportError:
        print("   [ERROR] Streamlit not installed!")
        return False
    
    # 5. Проверка Plotly
    print("\n5. Checking Plotly...")
    try:
        import plotly
        print(f"   [OK] Plotly installed (version {plotly.__version__})")
    except ImportError:
        print("   [ERROR] Plotly not installed!")
        return False
    
    print("\n=== [SUCCESS] All checks passed! ===")
    print("\nTo run dashboard execute:")
    print("  streamlit run dashboard/app.py")
    
    return True


if __name__ == "__main__":
    test_dashboard()
