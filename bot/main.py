"""
Главный модуль Telegram-бота TenderLens.

Команды:
- /start - Приветствие и инструкции
- /stats - Статистика по закупкам
- /search <запрос> - Поиск закупок
- /top_niches - Топ перспективных ниш
- /help - Справка по командам
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

from bot.config import (
    TELEGRAM_BOT_TOKEN,
    DATA_DIR,
    MAX_RESULTS_PER_PAGE,
)
from bot.data_loader import DataLoader

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Инициализация загрузчика данных
data_loader = DataLoader(DATA_DIR)


def format_price(price: float) -> str:
    """Форматирует цену в читаемый вид."""
    if price >= 1_000_000_000:
        return f"{price / 1_000_000_000:.2f} млрд ₽"
    elif price >= 1_000_000:
        return f"{price / 1_000_000:.2f} млн ₽"
    elif price >= 1_000:
        return f"{price / 1_000:.2f} тыс ₽"
    else:
        return f"{price:.2f} ₽"


def format_lot(lot: dict, index: int) -> str:
    """Форматирует информацию о лоте для отображения."""
    reg_number = lot.get("reg_number", "N/A")
    object_name = lot.get("object_name", "Без названия")[:100]
    price = lot.get("initial_price", 0)
    law = lot.get("law", "N/A")
    region = lot.get("region_name", "N/A")
    status = lot.get("status", "N/A")
    url = lot.get("url", "")
    
    text = f"<b>{index}. {object_name}</b>\n"
    text += f"📋 Номер: <code>{reg_number}</code>\n"
    text += f"💰 Цена: <b>{format_price(price)}</b>\n"
    text += f"📜 Закон: {law}\n"
    text += f"📍 Регион: {region}\n"
    text += f"📊 Статус: {status}\n"
    
    if url:
        text += f"🔗 <a href='{url}'>Открыть на zakupki.gov.ru</a>\n"
    
    return text


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    welcome_text = f"""
👋 Привет, {user.mention_html()}!

Я <b>TenderLens Bot</b> — твой помощник в анализе госзакупок России.

<b>Доступные команды:</b>
/stats — Статистика по закупкам
/search <запрос> — Поиск закупок
/top_niches — Топ перспективных ниш
/help — Справка по командам

<b>Что я умею:</b>
• Поиск закупок по ключевым словам
• Анализ статистики по регионам
• Определение перспективных ниш
• Алерты о новых закупках (скоро)

Начни с команды /stats чтобы увидеть общую статистику!
"""
    await update.message.reply_html(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    help_text = """
<b>📖 Справка по командам</b>

<b>/start</b> — Приветствие и инструкции

<b>/stats</b> — Общая статистика по закупкам
Показывает количество лотов, общий объем, средние цены и распределение по законам.

<b>/search [запрос]</b> — Поиск закупок
Примеры:
• <code>/search строительство</code>
• <code>/search медицинское оборудование</code>
• <code>/search ремонт дорог</code>

<b>/top_niches</b> — Топ-5 перспективных ниш
Показывает регионы с наибольшим объемом закупок.

<b>/help</b> — Эта справка

<b>💡 Советы:</b>
• Используйте конкретные ключевые слова для поиска
• Проверяйте статистику регулярно для отслеживания трендов
• Следите за перспективными нишами для поиска возможностей
"""
    await update.message.reply_html(help_text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /stats."""
    await update.message.reply_text("⏳ Загружаю статистику...")
    
    try:
        stats = data_loader.get_statistics()
        
        if stats["total_lots"] == 0:
            await update.message.reply_text("❌ Нет данных для отображения статистики.")
            return
        
        text = "<b>📊 Статистика по закупкам</b>\n\n"
        text += f"📦 Всего лотов: <b>{stats['total_lots']:,}</b>\n"
        text += f"💰 Общий объем: <b>{format_price(stats['total_volume'])}</b>\n"
        text += f"📈 Средняя цена: <b>{format_price(stats['avg_price'])}</b>\n"
        text += f"📊 Медианная цена: <b>{format_price(stats['median_price'])}</b>\n"
        text += f"🗺 Регионов: <b>{stats['regions_count']}</b>\n"
        text += f"🏢 Заказчиков: <b>{stats['customers_count']}</b>\n\n"
        
        text += "<b>📜 Распределение по законам:</b>\n"
        for law, count in stats['laws_distribution'].items():
            percentage = (count / stats['total_lots']) * 100
            text += f"• {law}: {count:,} ({percentage:.1f}%)\n"
        
        if stats['last_loaded']:
            text += f"\n🕐 Данные обновлены: {stats['last_loaded']}"
        
        await update.message.reply_html(text)
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await update.message.reply_text("❌ Ошибка при загрузке статистики. Попробуйте позже.")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /search."""
    if not context.args:
        await update.message.reply_html(
            "❌ Укажите запрос для поиска.\n\n"
            "<b>Пример:</b> <code>/search строительство</code>"
        )
        return
    
    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 Ищу закупки по запросу: <b>{query}</b>...", parse_mode="HTML")
    
    try:
        results = data_loader.search_lots(query=query, limit=MAX_RESULTS_PER_PAGE)
        
        if not results:
            await update.message.reply_text(
                f"❌ По запросу '<b>{query}</b>' ничего не найдено.\n\n"
                "Попробуйте изменить запрос или использовать другие ключевые слова.",
                parse_mode="HTML"
            )
            return
        
        text = f"<b>🔍 Результаты поиска: '{query}'</b>\n"
        text += f"Найдено: {len(results)} закупок\n\n"
        
        for i, lot in enumerate(results[:5], 1):
            text += format_lot(lot, i)
            text += "\n" + "─" * 40 + "\n\n"
        
        if len(results) > 5:
            text += f"<i>Показано 5 из {len(results)} результатов</i>"
        
        await update.message.reply_html(text, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        await update.message.reply_text("❌ Ошибка при поиске. Попробуйте позже.")


async def top_niches_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /top_niches."""
    await update.message.reply_text("⏳ Анализирую перспективные ниши...")
    
    try:
        top_niches = data_loader.get_top_niches(limit=5)
        
        if not top_niches:
            await update.message.reply_text("❌ Нет данных для анализа ниш.")
            return
        
        text = "<b>🎯 Топ-5 перспективных ниш (по регионам)</b>\n\n"
        
        for i, niche in enumerate(top_niches, 1):
            text += f"<b>{i}. {niche['region']}</b>\n"
            text += f"   📦 Лотов: {niche['count']:,}\n"
            text += f"   💰 Объем: {format_price(niche['volume'])}\n"
            text += f"   📈 Средняя цена: {format_price(niche['avg_price'])}\n\n"
        
        text += "<i>💡 Регионы с наибольшим объемом закупок — перспективные для участия</i>"
        
        await update.message.reply_html(text)
        
    except Exception as e:
        logger.error(f"Ошибка при анализе ниш: {e}")
        await update.message.reply_text("❌ Ошибка при анализе ниш. Попробуйте позже.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка при обработке команды. Попробуйте позже."
        )


def main() -> None:
    """Запуск бота."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен в .env файле!")
        print("\n❌ Ошибка: TELEGRAM_BOT_TOKEN не найден в .env файле")
        print("Добавьте токен бота в файл .env:")
        print("TELEGRAM_BOT_TOKEN=your-bot-token-here\n")
        return
    
    # Создание директории для логов
    Path("logs").mkdir(exist_ok=True)
    
    # Загрузка данных при старте
    logger.info("Загрузка данных...")
    lots = data_loader.load_lots()
    logger.info(f"Загружено {len(lots)} лотов")
    
    if not lots:
        logger.warning("Нет данных для работы бота!")
        print("\n⚠️  Предупреждение: Не найдено данных о закупках")
        print(f"Проверьте наличие JSON-файлов в директории: {DATA_DIR}\n")
    
    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("top_niches", top_niches_command))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    logger.info("Бот запущен!")
    print("\n✅ TenderLens Bot запущен!")
    print("Нажмите Ctrl+C для остановки\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
