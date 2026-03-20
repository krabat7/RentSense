"""
Telegram бот: уведомления о выгодных объявлениях по фильтрам.

Команды: /start, /help, /status, /on, /off, /filters, /set
Планировщик: каждый час с 9 до 23 — алерты; в 00:00 — сброс счётчиков.
"""
import asyncio
import logging
import os
from datetime import datetime, time
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
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
    get_available_metro_stations,
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

BUTTON_ON = "Уведомления: Вкл"
BUTTON_OFF = "Уведомления: Выкл"
BUTTON_FILTERS = "Мои фильтры"
BUTTON_CONFIGURE = "Настроить фильтры"
BUTTON_RESET = "Сбросить фильтры"
BUTTON_HELP = "Помощь"
BUTTON_BACK = "Назад"

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [BUTTON_ON, BUTTON_OFF],
        [BUTTON_FILTERS, BUTTON_CONFIGURE],
        [BUTTON_RESET, BUTTON_HELP],
    ],
    resize_keyboard=True,
)

MULTI_FILTER_KEYS = {"metro", "district", "rooms"}
NUMERIC_KEYS = {"rooms", "area_min", "area_max", "price_min", "price_max", "travel_time_max"}
EDITABLE_FILTER_KEYS = [
    "metro",
    "district",
    "rooms",
    "travel_time_max",
    "price_min",
    "price_max",
    "area_min",
    "area_max",
]


def _normalize_to_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v is not None and str(v).strip() != ""]
    if isinstance(value, str) and "," in value:
        return [x.strip() for x in value.split(",") if x.strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return [value] if value != "" else []


def _get_main_menu_text() -> str:
    return (
        "Главное меню:\n"
        "• включение/выключение уведомлений\n"
        "• просмотр и настройка фильтров\n"
        "• сброс фильтров"
    )


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
        reply_markup=MENU_KEYBOARD,
    )
    await update.message.reply_text(_get_main_menu_text(), reply_markup=MENU_KEYBOARD)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "/start — начать и создать профиль\n"
        "/on — включить уведомления\n"
        "/off — выключить уведомления\n"
        "/filters — текущие фильтры\n"
        "/set ключ значение — установить фильтр (или /set ключ сброс — сбросить один)\n"
        "/reset_filters — сбросить все фильтры\n"
        "/status — статус подписки и уведомлений за сегодня\n\n"
        "Также можно использовать кнопки внизу экрана."
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
        if isinstance(v, list):
            val = ", ".join(str(x) for x in v)
        else:
            val = str(v)
        lines.append(f"  {label}: {val}")
    return "\n".join(lines)


def _build_filter_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("Метро (мульти)", callback_data="cfg:metro:0")],
        [InlineKeyboardButton("Район (мульти)", callback_data="cfg:district")],
        [InlineKeyboardButton("Комнаты (мульти)", callback_data="cfg:rooms")],
        [InlineKeyboardButton("Время до метро", callback_data="cfg:travel_time_max")],
        [InlineKeyboardButton("Цена от", callback_data="cfg:price_min"), InlineKeyboardButton("Цена до", callback_data="cfg:price_max")],
        [InlineKeyboardButton("Площадь от", callback_data="cfg:area_min"), InlineKeyboardButton("Площадь до", callback_data="cfg:area_max")],
        [InlineKeyboardButton("Готово", callback_data="cfg:done")],
    ]
    return InlineKeyboardMarkup(rows)


def _build_rooms_menu(selected_rooms: list[int]) -> InlineKeyboardMarkup:
    selected = set(selected_rooms or [])
    rows = []
    row = []
    for r in [1, 2, 3, 4, 5]:
        mark = "✅" if r in selected else "☑️"
        row.append(InlineKeyboardButton(f"{mark} {r}", callback_data=f"cfgrooms:{r}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("Очистить", callback_data="cfgrooms:clear"), InlineKeyboardButton("Назад", callback_data="cfg:back")])
    return InlineKeyboardMarkup(rows)


async def _show_configure_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prefs = get_user_preferences(update.effective_user.id)
    await update.message.reply_text(
        "Выбор фильтра для настройки.\nТекущие:\n" + _format_filters(prefs),
        reply_markup=_build_filter_menu(),
    )


def _parse_list_text(raw: str):
    return [x.strip() for x in raw.split(",") if x.strip()]


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
    if key in MULTI_FILTER_KEYS:
        parts = _parse_list_text(value_raw)
        if key in NUMERIC_KEYS:
            parsed = []
            for p in parts:
                pv = _parse_set_value(key, p)
                if pv is None:
                    await update.message.reply_text(f"Неверное значение для «{key}»: {p}")
                    return
                parsed.append(pv)
            value = parsed
        else:
            value = parts
    else:
        value = _parse_set_value(key, value_raw)
    if value is None:
        await update.message.reply_text(f"Неверное значение для «{key}». Ожидается число.")
        return
    update_user_preferences(user_id, {key: value})
    label = FILTER_KEYS[key][0]
    await update.message.reply_text(f"Фильтр обновлён: {label} = {value}.")


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_get_main_menu_text(), reply_markup=MENU_KEYBOARD)


async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == BUTTON_ON:
        await cmd_on(update, context)
    elif text == BUTTON_OFF:
        await cmd_off(update, context)
    elif text == BUTTON_FILTERS:
        await filters_cmd(update, context)
    elif text == BUTTON_CONFIGURE:
        await _show_configure_filters(update, context)
    elif text == BUTTON_RESET:
        await reset_filters_cmd(update, context)
    elif text == BUTTON_HELP:
        await help_command(update, context)
    else:
        waiting = context.user_data.get("await_filter_input")
        if waiting:
            await _handle_filter_text_input(update, context, waiting)
            return
        await update.message.reply_text("Используйте кнопки меню или /help.", reply_markup=MENU_KEYBOARD)


def _metro_page_items(metros: list[str], page: int, page_size: int = 8):
    start = page * page_size
    end = start + page_size
    return metros[start:end], max(0, (len(metros) - 1) // page_size)


def _build_metro_menu(metros: list[str], selected: list[str], page: int) -> InlineKeyboardMarkup:
    current, max_page = _metro_page_items(metros, page)
    selected_set = set(selected or [])
    rows = []
    start_index = page * 8
    for i, station in enumerate(current):
        station_idx = start_index + i
        mark = "✅" if station in selected_set else "☑️"
        rows.append([InlineKeyboardButton(f"{mark} {station}", callback_data=f"cfgmetro:toggle:{page}:{station_idx}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"cfgmetro:page:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{max_page+1}", callback_data="cfgmetro:noop"))
    if page < max_page:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"cfgmetro:page:{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("Сохранить", callback_data="cfgmetro:save"), InlineKeyboardButton("Очистить", callback_data="cfgmetro:clear")])
    rows.append([InlineKeyboardButton("Назад", callback_data="cfg:back")])
    return InlineKeyboardMarkup(rows)


async def _handle_filter_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    user_id = update.effective_user.id
    raw = (update.message.text or "").strip()
    if key in MULTI_FILTER_KEYS:
        values = _parse_list_text(raw)
        if key in NUMERIC_KEYS:
            parsed = []
            for p in values:
                val = _parse_set_value(key, p)
                if val is None:
                    await update.message.reply_text(f"Неверный формат: {p}. Введите значения через запятую.", reply_markup=MENU_KEYBOARD)
                    return
                parsed.append(val)
            values = parsed
        update_user_preferences(user_id, {key: values})
    else:
        value = _parse_set_value(key, raw)
        if value is None:
            await update.message.reply_text("Неверный формат значения. Попробуйте еще раз.", reply_markup=MENU_KEYBOARD)
            return
        update_user_preferences(user_id, {key: value})
    context.user_data.pop("await_filter_input", None)
    await update.message.reply_text("Фильтр сохранен.", reply_markup=MENU_KEYBOARD)


def _get_available_metro(context: ContextTypes.DEFAULT_TYPE):
    metros = context.bot_data.get("metro_options")
    if not metros:
        return []
    return metros


async def callbacks_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    user_id = query.from_user.id
    prefs = get_user_preferences(user_id)

    if data.startswith("cfg:"):
        _, key, *rest = data.split(":")
        if key == "done":
            await query.edit_message_text("Настройка завершена.")
            return
        if key == "back":
            await query.edit_message_text("Выбор фильтра:", reply_markup=_build_filter_menu())
            return
        if key == "metro":
            page = int(rest[0]) if rest else 0
            selected = _normalize_to_list(prefs.get("metro"))
            await query.edit_message_text(
                "Выберите метро (можно несколько):",
                reply_markup=_build_metro_menu(_get_available_metro(context), selected, page),
            )
            return
        if key == "rooms":
            selected_raw = _normalize_to_list(prefs.get("rooms"))
            selected_rooms = [int(x) for x in selected_raw if str(x).isdigit()]
            await query.edit_message_text(
                "Выберите комнаты (можно несколько):",
                reply_markup=_build_rooms_menu(selected_rooms),
            )
            return
        if key == "district":
            context.user_data["await_filter_input"] = "district"
            await query.edit_message_text("Введите один или несколько районов через запятую.")
            return
        context.user_data["await_filter_input"] = key
        await query.edit_message_text(f"Введите значение для {key}.")
        return

    if data.startswith("cfgrooms:"):
        action = data.split(":")[1]
        current = _normalize_to_list(prefs.get("rooms"))
        current_int = [int(x) for x in current if str(x).isdigit()]
        if action == "clear":
            update_user_preferences(user_id, {"rooms": []})
            current_int = []
        else:
            value = int(action)
            if value in current_int:
                current_int.remove(value)
            else:
                current_int.append(value)
            current_int = sorted(set(current_int))
            update_user_preferences(user_id, {"rooms": current_int})
        await query.edit_message_text("Выберите комнаты (можно несколько):", reply_markup=_build_rooms_menu(current_int))
        return

    if data.startswith("cfgmetro:"):
        parts = data.split(":")
        action = parts[1]
        metros = _get_available_metro(context)
        selected = _normalize_to_list(prefs.get("metro"))
        if action == "noop":
            return
        if action == "page":
            page = int(parts[2])
            await query.edit_message_text(
                "Выберите метро (можно несколько):",
                reply_markup=_build_metro_menu(metros, selected, page),
            )
            return
        if action == "toggle":
            page = int(parts[2])
            station_idx = int(parts[3])
            if station_idx < 0 or station_idx >= len(metros):
                await query.edit_message_text(
                    "Список метро обновился, выберите заново.",
                    reply_markup=_build_metro_menu(metros, selected, 0),
                )
                return
            station = metros[station_idx]
            selected_set = set(selected)
            if station in selected_set:
                selected_set.remove(station)
            else:
                selected_set.add(station)
            selected = sorted(selected_set)
            update_user_preferences(user_id, {"metro": selected})
            await query.edit_message_text(
                "Выберите метро (можно несколько):",
                reply_markup=_build_metro_menu(metros, selected, page),
            )
            return
        if action == "clear":
            update_user_preferences(user_id, {"metro": []})
            await query.edit_message_text(
                "Выберите метро (можно несколько):",
                reply_markup=_build_metro_menu(metros, [], 0),
            )
            return
        if action == "save":
            await query.edit_message_text("Метро сохранено.", reply_markup=_build_filter_menu())
            return


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
    try:
        application.bot_data["metro_options"] = get_available_metro_stations(limit=500)
    except Exception as e:
        logger.warning("Не удалось загрузить список метро: %s", e)
        application.bot_data["metro_options"] = []

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_cmd))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("on", cmd_on))
    application.add_handler(CommandHandler("off", cmd_off))
    application.add_handler(CommandHandler("filters", filters_cmd))
    application.add_handler(CommandHandler("reset_filters", reset_filters_cmd))
    application.add_handler(CommandHandler("set", set_cmd))
    application.add_handler(CallbackQueryHandler(callbacks_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_router))

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
