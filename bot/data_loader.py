"""
Загрузка данных для бота из JSON или PostgreSQL.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataLoader:
    """Класс для загрузки данных о закупках."""
    
    def __init__(self, data_dir: Path):
        """
        Инициализация загрузчика данных.
        
        Args:
            data_dir: Путь к директории с JSON-файлами
        """
        self.data_dir = data_dir
        self.lots_cache: List[Dict] = []
        self.last_loaded: Optional[datetime] = None
    
    def get_latest_json_file(self) -> Optional[Path]:
        """
        Находит последний JSON-файл с лотами.
        
        Returns:
            Path к файлу или None
        """
        json_files = list(self.data_dir.glob("lots_*.json"))
        if not json_files:
            logger.warning(f"Не найдено JSON-файлов в {self.data_dir}")
            return None
        
        # Сортируем по размеру (больше лотов = лучше)
        json_files.sort(key=lambda f: f.stat().st_size, reverse=True)
        return json_files[0]
    
    def load_lots(self, force_reload: bool = False) -> List[Dict]:
        """
        Загружает лоты из JSON-файла.
        
        Args:
            force_reload: Принудительная перезагрузка данных
            
        Returns:
            Список лотов
        """
        if self.lots_cache and not force_reload:
            return self.lots_cache
        
        json_file = self.get_latest_json_file()
        if not json_file:
            logger.error("Не найдено файлов с данными")
            return []
        
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                self.lots_cache = json.load(f)
            self.last_loaded = datetime.now()
            logger.info(f"Загружено {len(self.lots_cache)} лотов из {json_file.name}")
            return self.lots_cache
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return []
    
    def search_lots(
        self,
        query: Optional[str] = None,
        region_code: Optional[str] = None,
        law: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Поиск лотов по критериям.
        
        Args:
            query: Текстовый поиск в названии
            region_code: Код региона
            law: Закон (44-ФЗ, 223-ФЗ)
            min_price: Минимальная цена
            max_price: Максимальная цена
            limit: Максимальное количество результатов
            
        Returns:
            Список найденных лотов
        """
        lots = self.load_lots()
        results = []
        
        for lot in lots:
            # Фильтр по тексту
            if query:
                query_lower = query.lower()
                if query_lower not in lot.get("object_name", "").lower():
                    continue
            
            # Фильтр по региону
            if region_code and lot.get("region_code") != region_code:
                continue
            
            # Фильтр по закону
            if law and lot.get("law") != law:
                continue
            
            # Фильтр по цене
            price = lot.get("initial_price", 0)
            if min_price and price < min_price:
                continue
            if max_price and price > max_price:
                continue
            
            results.append(lot)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_statistics(self) -> Dict:
        """
        Получает статистику по загруженным данным.
        
        Returns:
            Словарь со статистикой
        """
        lots = self.load_lots()
        
        if not lots:
            return {
                "total_lots": 0,
                "total_volume": 0,
                "avg_price": 0,
                "regions_count": 0,
                "customers_count": 0,
            }
        
        total_volume = sum(lot.get("initial_price", 0) for lot in lots)
        regions = set(lot.get("region_code") for lot in lots if lot.get("region_code"))
        customers = set(lot.get("customer_url") for lot in lots if lot.get("customer_url"))
        
        # Распределение по законам
        laws_dist = {}
        for lot in lots:
            law = lot.get("law", "Неизвестно")
            laws_dist[law] = laws_dist.get(law, 0) + 1
        
        return {
            "total_lots": len(lots),
            "total_volume": total_volume,
            "avg_price": total_volume / len(lots) if lots else 0,
            "median_price": sorted([lot.get("initial_price", 0) for lot in lots])[len(lots) // 2] if lots else 0,
            "regions_count": len(regions),
            "customers_count": len(customers),
            "laws_distribution": laws_dist,
            "last_loaded": self.last_loaded.strftime("%Y-%m-%d %H:%M:%S") if self.last_loaded else None,
        }
    
    def get_top_niches(self, limit: int = 5) -> List[Dict]:
        """
        Получает топ перспективных ниш.
        
        Args:
            limit: Количество ниш
            
        Returns:
            Список ниш с метриками
        """
        lots = self.load_lots()
        
        # Группировка по регионам
        regions_data = {}
        for lot in lots:
            region = lot.get("region_name", "Неизвестно")
            if region not in regions_data:
                regions_data[region] = {
                    "region": region,
                    "count": 0,
                    "volume": 0,
                    "avg_price": 0,
                }
            
            regions_data[region]["count"] += 1
            regions_data[region]["volume"] += lot.get("initial_price", 0)
        
        # Расчет средней цены
        for region_data in regions_data.values():
            if region_data["count"] > 0:
                region_data["avg_price"] = region_data["volume"] / region_data["count"]
        
        # Сортировка по объему
        top_regions = sorted(
            regions_data.values(),
            key=lambda x: x["volume"],
            reverse=True
        )[:limit]
        
        return top_regions
