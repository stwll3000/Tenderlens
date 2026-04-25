"""
Обогащение 100 лотов детальной информацией.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

from scraper.enrich_existing_lots import LotEnricher
from pathlib import Path
from datetime import datetime

# Создаём директорию для логов
Path("logs").mkdir(exist_ok=True)

# Пути к файлам
input_file = "data/lots_multi_regions_6000_20260425.json"
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"data/lots_enriched_100_{timestamp}.json"

# Создаём enricher
enricher = LotEnricher(delay_min=2, delay_max=4)

# Обогащаем 100 лотов
print("Обогащение 100 лотов детальной информацией...")
print("Это займёт ~8-10 минут")
enricher.enrich_lots_from_file(
    input_file=input_file,
    output_file=output_file,
    max_lots=100,
    save_every=10
)

print(f"\nГотово! Файл: {output_file}")
