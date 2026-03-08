"""
Telegram бот: уведомления о выгодных объявлениях по фильтрам.

Команды: /start, /help, /status, /on, /off, /filters, /set
Планировщик: каждый час с 9 до 23 — алерты; в 00:00 — сброс счётчиков.
"""
import asyncio
import logging
import os
from datetime import datetime, time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import dotenv_values
from pathlib import Path

from .database import (
    init_bot_tables,
    get_user,
    create_user,
    get_user_preferences,
    update_user_preferences,
    clear_user_preferences,
    set_user_active,
)

logger = logging.getLogger(__name__)

env_path = Path(__file__).parent.parent.parent / '.env'
env = dotenv_values(env_path)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or env.get('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env")

# Ключи фильтров и подсказки для пользователя
FILTER_KEYS = {
    'district': ('Район', str),
    'rooms': ('Комнаты', int),
    'area_min': ('Площадь от (м²)', float),
    'area_max': ('Площадь до (м²)', float),
    'price_min': ('Цена от (руб)', (int, float)),
    'price_max': ('Цена до (руб)', (int, float)),
    'metro': ('Метро', str),
    'travel_time_max': ('Время до метро до (мин)', int),
}


def _get_or_create_user(user_id: int, chat_id: int):
    user = get_user(user_id)
    if not user:
        user = create_user(user_id, chat_id)
    return user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _get_or_create_user(update.effective_user.id, update.effective_chat.id)
    await update.message.reply_text(
        "Привет! Я бот RentSense.\n\n"
        "Я присылаю *выгодные* объявления за сегодня: где прогноз модели выше реальной цены.\n\n"
        "• /on — включить уведомления\n"
        "• /off — выключить уведомления\n"
        "• /filters — посмотреть свои фильтры\n"
        "• /set ключ значение — задать фильтр (например: /set district Пресненский)\n"
        "• /reset_filters — сбросить все фильтры\n"
        "• /status — статус и счётчик уведомлений\n\n"
        "Уведомления приходят с 9 до 23 по одному объявлению за раз. Если за день подходящих нет — пришлю подсказку расширить фильтры.",
        parse_mode='Markdown',
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "/start — начать и создать профиль\n"
        "/on — включить уведомления\n"
        "/off — выключить уведомления\n"
        "/filters — текущие фильтры\n"
        "/set ключ значение — установить фильтр (или /set ключ сброс — сбросить один)\n"
        "/reset_filters — сбросить все фильтры\n"
        "/status — статус подписки и уведомлений за сегодня"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _get_or_create_user(user_id, update.effective_chat.id)
    user = get_user(user_id)
    prefs = get_user_preferences(user_id)
    status_text = "✅ Уведомления включены" if user.is_active else "❌ Уведомления выключены"
    msg = (
        f"{status_text}\n"
        f"Уведомлений сегодня: {user.alerts_today}\n"
    )
    if prefs:
        msg += "\nФильтры:\n"
        for k, v in prefs.items():
            label = FILTER_KEYS.get(k, (k, str))[0]
            msg += f"  • {label}: {v}\n"
    else:
        msg += "\nФильтры не заданы — учитываются все объявления за сегодня."
    await update.message.reply_text(msg)


async def cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _get_or_create_user(user_id, update.effective_chat.id)
    set_user_active(user_id, True)
    await update.message.reply_text("Уведомления включены. Буду присылать выгодные объявления по вашим фильтрам.")


async def cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _get_or_create_user(user_id, update.effective_chat.id)
    set_user_active(user_id, False)
    await update.message.reply_text("Уведомления выключены. Чтобы снова получать объявления — /on.")


def _format_filters(prefs: dict) -> str:
    if not prefs:
        return "Не заданы. Будут учитываться все объявления за сегодня."
    lines = []
    for k, v in prefs.items():
        label = FILTER_KEYS.get(k, (k, str))[0]
        lines.append(f"  {label}: {v}")
    return "\n".join(lines)


async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prefs = get_user_preferences(user_id)
    msg = "Ваши фильтры:\n\n" + _format_filters(prefs)
    msg += "\n\nЧтобы изменить: /set ключ значение\nСбросить один: /set ключ сброс\nСбросить все: /reset_filters"
    await update.message.reply_text(msg)


async def reset_filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбросить все фильтры."""
    user_id = update.effective_user.id
    _get_or_create_user(user_id, update.effective_chat.id)
    clear_user_preferences(user_id)
    await update.message.reply_text("Все фильтры сброшены. Будут учитываться все объявления за сегодня.")


def _parse_set_value(key: str, raw: str):
    if key not in FILTER_KEYS:
        return raw
    typ = FILTER_KEYS[key][1]
    if typ is str:
        return raw.strip()
    if typ is int:
        try:
            return int(raw.strip().replace(' ', ''))
        except ValueError:
            return None
    if typ is float:
        try:
            return float(raw.strip().replace(',', '.').replace(' ', ''))
        except ValueError:
            return None
    if isinstance(typ, tuple) and (int in typ or float in typ):
        try:
            return int(raw.strip().replace(' ', ''))
        except ValueError:
            try:
                return float(raw.strip().replace(',', '.').replace(' ', ''))
            except ValueError:
                return None
    return raw.strip()


async def set_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _get_or_create_user(user_id, update.effective_chat.id)
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /set ключ значение\n"
            "Примеры:\n"
            "/set district Пресненский\n"
            "/set rooms 2\n"
            "/set price_max 80000\n"
            "Ключи: district, rooms, area_min, area_max, price_min, price_max, metro, travel_time_max"
        )
        return
    key = context.args[0].lower().strip()
    if key not in FILTER_KEYS:
        await update.message.reply_text(
            f"Неизвестный ключ «{key}». Доступны: " + ", ".join(FILTER_KEYS.keys())
        )
        return
    value_raw = " ".join(context.args[1:]).strip() if len(context.args) > 1 else ""
    if value_raw.lower() in ("сброс", "clear", "удалить", ""):
        update_user_preferences(user_id, {key: None})
        await update.message.reply_text(f"Фильтр «{key}» сброшен.")
        return
    value = _parse_set_value(key, value_raw)
    if value is None:
        await update.message.reply_text(f"Неверное значение для «{key}». Ожидается число.")
        return
    update_user_preferences(user_id, {key: value})
    label = FILTER_KEYS[key][0]
    await update.message.reply_text(f"Фильтр обновлён: {label} = {value}.")


async def _hourly_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Запуск отправки алертов каждый час (только с 9 до 23)."""
    from .scheduler import ALERT_HOUR_START, ALERT_HOUR_END, send_alerts
    if ALERT_HOUR_START <= datetime.now().hour <= ALERT_HOUR_END:
        try:
            await send_alerts()
        except Exception as e:
            logger.exception("Ошибка в hourly_alerts: %s", e)


async def _daily_reset(context: ContextTypes.DEFAULT_TYPE):
    """Сброс счётчиков алертов в 00:00."""
    from .scheduler import run_reset_daily
    await asyncio.to_thread(run_reset_daily)


def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен")
        return

    init_bot_tables()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("on", cmd_on))
    application.add_handler(CommandHandler("off", cmd_off))
    application.add_handler(CommandHandler("filters", filters_cmd))
    application.add_handler(CommandHandler("reset_filters", reset_filters_cmd))
    application.add_handler(CommandHandler("set", set_cmd))

    if application.job_queue:
        application.job_queue.run_repeating(
            _hourly_alerts,
            interval=3600,
            first=60,
        )
        application.job_queue.run_daily(
            _daily_reset,
            time=time(0, 0, 0),
        )
        logger.info("Планировщик: алерты каждый час 9–23, сброс в 00:00")
    else:
        logger.warning(
            "Job queue недоступен (требуется python-telegram-bot[job-queue]). "
            "Алерты по расписанию отключены."
        )

    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
    )
    main()
