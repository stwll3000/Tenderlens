"""
Конфигурация Telegram-бота.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Bot settings
MAX_RESULTS_PER_PAGE = 10
ALERT_CHECK_INTERVAL = 3600  # 1 час в секундах
MIN_PRICE_FOR_ALERT = 1_000_000  # 1 млн рублей

# Критерии для алертов о перспективных закупках
ALERT_CRITERIA = {
    "min_price": 500_000,  # минимальная цена для алерта
    "max_price": 50_000_000,  # максимальная цена
    "preferred_laws": ["44-ФЗ"],  # предпочитаемые законы
    "exclude_statuses": ["Закупка отменена", "Закупка завершена"],
}
