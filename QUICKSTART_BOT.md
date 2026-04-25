# TenderLens — Быстрый старт с Telegram-ботом

## 🚀 Запуск бота за 5 минут

### 1. Установите зависимости

```bash
pip install python-telegram-bot==20.7
```

### 2. Создайте бота в Telegram

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Укажите имя: `TenderLens Bot`
4. Укажите username: `tenderlens_bot` (или другой доступный)
5. **Скопируйте токен** (например: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 3. Обновите .env файл

Откройте `.env` и замените:

```env
TELEGRAM_BOT_TOKEN=ваш-токен-от-botfather
```

### 4. Запустите бота

```bash
python bot/main.py
```

Вы увидите:
```
✅ TenderLens Bot запущен!
Нажмите Ctrl+C для остановки
```

### 5. Протестируйте в Telegram

Найдите вашего бота в Telegram и попробуйте команды:

- `/start` — приветствие
- `/stats` — статистика по 6000 закупкам
- `/search строительство` — поиск закупок
- `/top_niches` — топ-5 регионов

---

## 📋 Доступные команды

| Команда | Описание | Пример |
|---------|----------|--------|
| `/start` | Приветствие и инструкции | `/start` |
| `/help` | Справка по командам | `/help` |
| `/stats` | Статистика по закупкам | `/stats` |
| `/search` | Поиск закупок | `/search медицинское оборудование` |
| `/top_niches` | Топ-5 перспективных ниш | `/top_niches` |

---

## 🔧 Настройка Supabase (опционально)

Бот работает с JSON-файлами из коробки. Для подключения PostgreSQL:

1. Откройте [Supabase Dashboard](https://supabase.com/dashboard)
2. Получите новый connection string
3. Следуйте инструкциям в [SETUP_SUPABASE.md](SETUP_SUPABASE.md)

---

## 📊 Что умеет бот

✅ Поиск по 6000 закупкам  
✅ Статистика по регионам и законам  
✅ Анализ перспективных ниш  
✅ Форматированный вывод с ценами  
✅ Ссылки на zakupki.gov.ru  

---

## 🐛 Проблемы?

### Бот не запускается
- Проверьте токен в `.env`
- Убедитесь, что установлен `python-telegram-bot`

### Нет данных
- Убедитесь, что в `data/` есть JSON-файлы
- Запустите парсер: `python scraper/collect_multi_regions.py`

### Другие вопросы
- Читайте [bot/README.md](bot/README.md)
- Читайте [SETUP_SUPABASE.md](SETUP_SUPABASE.md)

---

**Готово!** Теперь у вас работает Telegram-бот для мониторинга госзакупок 🎉
