"""
Скрипт для инициализации базы данных TenderLens.

Выполняет:
1. Проверку подключения к PostgreSQL
2. Создание таблиц
3. Загрузку начальных данных (регионы + лоты из JSON)

Использование:
    python db/init_database.py
"""

import logging
import sys
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция инициализации БД."""
    print("\n" + "=" * 70)
    print("  ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ TENDERLENS")
    print("=" * 70 + "\n")
    
    try:
        # Шаг 1: Проверка подключения
        print("[1/4] Проверка подключения к PostgreSQL...")
        from db.connection import test_connection
        
        if not test_connection():
            print("\n❌ ОШИБКА: Не удалось подключиться к БД")
            print("\nПроверьте:")
            print("  1. Создан ли файл .env с DATABASE_URL")
            print("  2. Правильность строки подключения")
            print("  3. Доступность Supabase")
            print("\nИнструкция: см. SETUP_DATABASE.md")
            sys.exit(1)
        
        print("✓ Подключение успешно\n")
        
        # Шаг 2: Создание таблиц
        print("[2/4] Создание таблиц в БД...")
        from db.connection import init_db
        init_db()
        print("✓ Таблицы созданы\n")
        
        # Шаг 3: Загрузка регионов
        print("[3/4] Загрузка справочника регионов...")
        from db.connection import SessionLocal
        from db.loader import load_regions
        
        db = SessionLocal()
        try:
            load_regions(db)
            print("✓ Регионы загружены\n")
        finally:
            db.close()
        
        # Шаг 4: Загрузка лотов
        print("[4/4] Загрузка лотов из JSON...")
        json_path = Path("data/lots_all_20260425_173650.json")
        
        if not json_path.exists():
            print(f"⚠ Файл {json_path} не найден")
            print("  Пропускаем загрузку лотов")
            print("  Запустите парсер: python scraper/fetch_lots.py")
        else:
            from db.loader import load_lots_from_json
            db = SessionLocal()
            try:
                loaded = load_lots_from_json(str(json_path), db)
                print(f"✓ Загружено {loaded} лотов\n")
            finally:
                db.close()
        
        # Финальная статистика
        print("=" * 70)
        print("  СТАТИСТИКА БАЗЫ ДАННЫХ")
        print("=" * 70)
        
        from db.loader import get_stats
        db = SessionLocal()
        try:
            stats = get_stats(db)
            print(f"\n  📊 Регионов:    {stats['regions']}")
            print(f"  🏢 Заказчиков:  {stats['customers']}")
            print(f"  📦 Лотов:       {stats['lots']}")
        finally:
            db.close()
        
        print("\n" + "=" * 70)
        print("  ✅ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 70 + "\n")
        
        print("Следующие шаги:")
        print("  1. Проверьте данные в Supabase Dashboard")
        print("  2. Запустите парсер для сбора большего количества лотов:")
        print("     python scraper/fetch_lots.py")
        print("  3. Начните аналитику в Jupyter:")
        print("     jupyter notebook notebooks/")
        print()
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        logger.exception("Детали ошибки:")
        sys.exit(1)


if __name__ == "__main__":
    main()
