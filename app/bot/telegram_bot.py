"""
Telegram бот: уведомления о выгодных объявлениях по фильтрам.

Команды: /start, /help, /status, /on, /off, /filters, /set
Планировщик: каждый час с 9 до 23 — алерты; в 00:00 — сброс счётчиков.
"""
import asyncio
import logging
import os
import unicodedata
from datetime import datetime, time
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.error import BadRequest
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
BUTTON_STATUS = "Статус"
BUTTON_BACK = "Назад"


def build_main_keyboard(is_active: bool) -> ReplyKeyboardMarkup:
    """Одна кнопка: при включённых уведомлениях — «Выкл», при выключенных — «Вкл»."""
    toggle = BUTTON_OFF if is_active else BUTTON_ON
    return ReplyKeyboardMarkup(
        [
            [toggle],
            [BUTTON_FILTERS, BUTTON_CONFIGURE],
            [BUTTON_RESET, BUTTON_HELP],
            [BUTTON_STATUS],
        ],
        resize_keyboard=True,
    )


def _user_notifications_active(user_id: int) -> bool:
    u = get_user(user_id)
    if not u:
        return True
    return bool(u.is_active)


async def main_keyboard_for_user(user_id: int) -> ReplyKeyboardMarkup:
    is_active = await asyncio.to_thread(_user_notifications_active, user_id)
    return build_main_keyboard(is_active)


def _clear_filter_wizard(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сброс мастера фильтров: ожидание текста и черновики inline (метро/комнаты)."""
    context.user_data.pop("await_filter_input", None)
    context.user_data.pop("filter_draft_metro", None)
    context.user_data.pop("filter_draft_rooms", None)


async def _safe_query_edit(query, text: str, reply_markup=None) -> None:
    """Telegram возвращает 400, если текст и клавиатура не изменились — не считаем это ошибкой."""
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as e:
        msg = str(e).lower()
        if "message is not modified" in msg or "not modified" in msg:
            return
        raise


def _parse_cfg_callback(data: str) -> tuple[str | None, list[str]]:
    """Разбор cfg:… без ломания ключей вроде travel_time_max."""
    if not data.startswith("cfg:"):
        return None, []
    tail = data[4:]
    if not tail:
        return None, []
    if ":" in tail:
        key, rest0 = tail.split(":", 1)
        return key, [rest0]
    return tail, []


async def _update_prefs_in_thread(user_id: int, updates: dict) -> None:
    await asyncio.to_thread(update_user_preferences, user_id, updates)


def _sync_status_payload(user_id: int, chat_id: int) -> tuple[str, bool]:
    """Текст статуса + is_active для клавиатуры — один заход в БД по сути."""
    user = _get_or_create_user(user_id, chat_id)
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
            if isinstance(v, list):
                val = ", ".join(str(x) for x in v)
            else:
                val = str(v)
            msg += f"  • {label}: {val}\n"
    else:
        msg += "\nФильтры не заданы — учитываются все объявления за сегодня."
    return msg, bool(user.is_active)


def _sync_start_keyboard_state(user_id: int, chat_id: int) -> bool:
    _get_or_create_user(user_id, chat_id)
    return _user_notifications_active(user_id)


def _sync_filters_and_active(user_id: int) -> tuple[dict, bool]:
    prefs = get_user_preferences(user_id)
    active = _user_notifications_active(user_id)
    return prefs, active


def _normalize_menu_text(s: str) -> str:
    """Невидимые символы и полноширинное двоеточие — для совпадения с текстом кнопок Telegram."""
    t = unicodedata.normalize("NFC", (s or "").strip())
    for ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"):
        t = t.replace(ch, "")
    t = t.replace("\uff1a", ":")
    return t


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
        "• одна кнопка уведомлений: «Вкл» или «Выкл» по текущему состоянию\n"
        "• «Статус» — подписка и счётчик за день\n"
        "• фильтры: просмотр и настройка\n"
        "• сброс фильтров"
    )


def _get_or_create_user(user_id: int, chat_id: int):
    user = get_user(user_id)
    if not user:
        user = create_user(user_id, chat_id)
    return user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_filter_wizard(context)
    uid = update.effective_user.id
    cid = update.effective_chat.id
    is_active = await asyncio.to_thread(_sync_start_keyboard_state, uid, cid)
    kb = build_main_keyboard(is_active)
    await update.message.reply_text(
        "Привет! Я бот RentSense.\n\n"
        "Я присылаю *выгодные* объявления за сегодня: где прогноз модели выше реальной цены.\n\n"
        "• Кнопка *Уведомления* — включить или выключить (подпись меняется)\n"
        "• /filters — посмотреть свои фильтры\n"
        "• /set ключ значение — задать фильтр (например: /set district Пресненский)\n"
        "• /reset_filters — сбросить все фильтры\n"
        "• /status или кнопка «Статус»\n\n"
        "Уведомления приходят с 9 до 23 по одному объявлению за раз. Если за день подходящих нет — пришлю подсказку расширить фильтры.",
        parse_mode='Markdown',
        reply_markup=kb,
    )
    await update.message.reply_text(_get_main_menu_text(), reply_markup=kb)


HELP_TEXT = (
    "Команды:\n"
    "/start — начать и создать профиль\n"
    "/on — включить уведомления\n"
    "/off — выключить уведомления\n"
    "/filters — текущие фильтры\n"
    "/set ключ значение — установить фильтр (или /set ключ сброс — сбросить один)\n"
    "/reset_filters — сбросить все фильтры\n"
    "/status — статус подписки и уведомлений за сегодня\n"
    "/cancel — отменить ввод фильтра (если бот ждёт текст)\n\n"
    "Кнопки внизу: одна кнопка уведомлений (Вкл/Выкл по состоянию), «Статус», фильтры."
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_filter_wizard(context)
    uid = update.effective_user.id
    try:
        kb = await main_keyboard_for_user(uid)
        await update.message.reply_text(HELP_TEXT, reply_markup=kb)
    except BadRequest as e:
        logger.warning("help_command: не удалось отправить клавиатуру: %s", e)
        await update.message.reply_text(HELP_TEXT)
        try:
            kb = await main_keyboard_for_user(uid)
            await update.message.reply_text("\u2060", reply_markup=kb)
        except BadRequest as e2:
            logger.warning("help_command: повторная клавиатура не прошла: %s", e2)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_filter_wizard(context)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        msg, is_active = await asyncio.to_thread(_sync_status_payload, user_id, chat_id)
    except Exception:
        logger.exception("status: ошибка БД user_id=%s", user_id)
        await update.message.reply_text(
            "Не удалось загрузить статус (БД).",
            reply_markup=await main_keyboard_for_user(user_id),
        )
        return
    kb = build_main_keyboard(is_active)
    try:
        await update.message.reply_text(msg, reply_markup=kb)
    except BadRequest as e:
        logger.warning("status: reply с клавиатурой не прошёл: %s", e)
        await update.message.reply_text(msg)
        try:
            await update.message.reply_text("\u2060", reply_markup=kb)
        except BadRequest as e2:
            logger.warning("status: повтор клавиатуры: %s", e2)


def _sync_cmd_on(user_id: int, chat_id: int):
    _get_or_create_user(user_id, chat_id)
    set_user_active(user_id, True)


def _sync_cmd_off(user_id: int, chat_id: int):
    _get_or_create_user(user_id, chat_id)
    set_user_active(user_id, False)


async def cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_filter_wizard(context)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        await asyncio.to_thread(_sync_cmd_on, user_id, chat_id)
    except Exception:
        logger.exception("cmd_on: ошибка БД user_id=%s", user_id)
        await update.message.reply_text(
            "Не удалось сохранить настройки (нет связи с БД). Проверьте контейнер mysql и переменные DB_*.",
            reply_markup=await main_keyboard_for_user(user_id),
        )
        return
    await update.message.reply_text(
        "Уведомления включены. Буду присылать выгодные объявления по вашим фильтрам.",
        reply_markup=build_main_keyboard(True),
    )


async def cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_filter_wizard(context)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        await asyncio.to_thread(_sync_cmd_off, user_id, chat_id)
    except Exception:
        logger.exception("cmd_off: ошибка БД user_id=%s", user_id)
        await update.message.reply_text(
            "Не удалось сохранить настройки (нет связи с БД).",
            reply_markup=await main_keyboard_for_user(user_id),
        )
        return
    await update.message.reply_text(
        "Уведомления выключены. Чтобы снова получать объявления — кнопка «Уведомления: Вкл» или /on.",
        reply_markup=build_main_keyboard(False),
    )


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
    uid = update.effective_user.id
    try:
        prefs = await asyncio.to_thread(get_user_preferences, uid)
    except Exception:
        logger.exception("_show_configure_filters: БД uid=%s", uid)
        await update.message.reply_text(
            "Не удалось загрузить фильтры (БД).",
            reply_markup=await main_keyboard_for_user(uid),
        )
        return
    await update.message.reply_text(
        "Выбор фильтра для настройки.\nТекущие:\n" + _format_filters(prefs),
        reply_markup=_build_filter_menu(),
    )


def _parse_list_text(raw: str):
    return [x.strip() for x in raw.split(",") if x.strip()]


async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_filter_wizard(context)
    user_id = update.effective_user.id
    try:
        prefs, is_active = await asyncio.to_thread(_sync_filters_and_active, user_id)
    except Exception:
        logger.exception("filters_cmd: ошибка БД user_id=%s", user_id)
        await update.message.reply_text(
            "Не удалось загрузить фильтры (нет связи с БД).",
            reply_markup=await main_keyboard_for_user(user_id),
        )
        return
    msg = "Ваши фильтры:\n\n" + _format_filters(prefs)
    msg += "\n\nЧтобы изменить: /set ключ значение\nСбросить один: /set ключ сброс\nСбросить все: /reset_filters"
    await update.message.reply_text(msg, reply_markup=build_main_keyboard(is_active))


def _sync_reset_filters(user_id: int, chat_id: int):
    _get_or_create_user(user_id, chat_id)
    clear_user_preferences(user_id)


async def reset_filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбросить все фильтры."""
    _clear_filter_wizard(context)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        await asyncio.to_thread(_sync_reset_filters, user_id, chat_id)
    except Exception:
        logger.exception("reset_filters_cmd: ошибка БД user_id=%s", user_id)
        await update.message.reply_text(
            "Не удалось сбросить фильтры (нет связи с БД).",
            reply_markup=await main_keyboard_for_user(user_id),
        )
        return
    await update.message.reply_text(
        "Все фильтры сброшены. Будут учитываться все объявления за сегодня.",
        reply_markup=await main_keyboard_for_user(user_id),
    )


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
    chat_id = update.effective_chat.id
    await asyncio.to_thread(_get_or_create_user, user_id, chat_id)
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
        await _update_prefs_in_thread(user_id, {key: None})
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
    await _update_prefs_in_thread(user_id, {key: value})
    label = FILTER_KEYS[key][0]
    await update.message.reply_text(f"Фильтр обновлён: {label} = {value}.")


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear_filter_wizard(context)
    uid = update.effective_user.id
    kb = await main_keyboard_for_user(uid)
    await update.message.reply_text(_get_main_menu_text(), reply_markup=kb)


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    had = "await_filter_input" in context.user_data
    _clear_filter_wizard(context)
    uid = update.effective_user.id
    msg = "Ввод фильтра отменён." if had else "Сейчас бот не ждёт ввод фильтра."
    await update.message.reply_text(msg, reply_markup=await main_keyboard_for_user(uid))


async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = _normalize_menu_text(update.message.text or "")
    norm_on = _normalize_menu_text(BUTTON_ON)
    norm_off = _normalize_menu_text(BUTTON_OFF)
    norm_filters = _normalize_menu_text(BUTTON_FILTERS)
    norm_configure = _normalize_menu_text(BUTTON_CONFIGURE)
    norm_reset = _normalize_menu_text(BUTTON_RESET)
    norm_help = _normalize_menu_text(BUTTON_HELP)
    norm_status = _normalize_menu_text(BUTTON_STATUS)
    if text in (
        norm_on,
        norm_off,
        norm_filters,
        norm_configure,
        norm_reset,
        norm_help,
        norm_status,
    ):
        _clear_filter_wizard(context)
    if text == norm_on:
        await cmd_on(update, context)
    elif text == norm_off:
        await cmd_off(update, context)
    elif text == norm_filters:
        await filters_cmd(update, context)
    elif text == norm_configure:
        await _show_configure_filters(update, context)
    elif text == norm_reset:
        await reset_filters_cmd(update, context)
    elif text == norm_help:
        await help_command(update, context)
    elif text == norm_status:
        await status(update, context)
    else:
        waiting = context.user_data.get("await_filter_input")
        if waiting:
            await _handle_filter_text_input(update, context, waiting)
            return
        uid = update.effective_user.id
        logger.debug(
            "button_router: неизвестный текст user_id=%s repr=%r",
            uid,
            update.message.text,
        )
        await update.message.reply_text(
            "Используйте кнопки меню или /help.",
            reply_markup=await main_keyboard_for_user(uid),
        )


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
    chat_id = update.effective_chat.id
    raw = (update.message.text or "").strip()
    try:
        await asyncio.to_thread(_get_or_create_user, user_id, chat_id)
        if key in MULTI_FILTER_KEYS:
            values = _parse_list_text(raw)
            if key in NUMERIC_KEYS:
                parsed = []
                for p in values:
                    val = _parse_set_value(key, p)
                    if val is None:
                        await update.message.reply_text(
                            f"Неверный формат: {p}. Введите значения через запятую.",
                            reply_markup=await main_keyboard_for_user(user_id),
                        )
                        return
                    parsed.append(val)
                values = parsed
            await _update_prefs_in_thread(user_id, {key: values})
        else:
            value = _parse_set_value(key, raw)
            if value is None:
                await update.message.reply_text(
                    "Неверный формат значения. Попробуйте еще раз.",
                    reply_markup=await main_keyboard_for_user(user_id),
                )
                return
            await _update_prefs_in_thread(user_id, {key: value})
    except Exception:
        logger.exception("filter_text_input user_id=%s key=%s", user_id, key)
        await update.message.reply_text(
            "Не удалось сохранить фильтр (БД). Попробуйте позже или /cancel.",
            reply_markup=await main_keyboard_for_user(user_id),
        )
        return
    context.user_data.pop("await_filter_input", None)
    await update.message.reply_text(
        "Фильтр сохранен.",
        reply_markup=await main_keyboard_for_user(user_id),
    )


def _get_available_metro(context: ContextTypes.DEFAULT_TYPE):
    metros = context.bot_data.get("metro_options")
    if not metros:
        return []
    return metros


async def callbacks_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    data = query.data or ""
    user_id = query.from_user.id

    if data.startswith("cfg:"):
        key, rest = _parse_cfg_callback(data)
        if key is None:
            return
        if key == "done":
            context.user_data.pop("filter_draft_metro", None)
            context.user_data.pop("filter_draft_rooms", None)
            await _safe_query_edit(query, "Настройка завершена. Клавиатура снизу — главное меню.")
            return
        if key == "back":
            context.user_data.pop("filter_draft_metro", None)
            context.user_data.pop("filter_draft_rooms", None)
            await _safe_query_edit(query, "Выбор фильтра:", reply_markup=_build_filter_menu())
            return
        if key == "metro":
            page = int(rest[0]) if rest else 0
            try:
                prefs = await asyncio.to_thread(get_user_preferences, user_id)
            except Exception:
                logger.exception("callbacks_router metro open user_id=%s", user_id)
                await _safe_query_edit(query, "Ошибка БД. Попробуйте /start.")
                return
            selected = _normalize_to_list(prefs.get("metro"))
            context.user_data["filter_draft_metro"] = list(selected)
            metros = _get_available_metro(context)
            await _safe_query_edit(
                "Выберите метро (можно несколько), затем «Сохранить»:",
                reply_markup=_build_metro_menu(metros, selected, page),
            )
            return
        if key == "rooms":
            try:
                prefs = await asyncio.to_thread(get_user_preferences, user_id)
            except Exception:
                logger.exception("callbacks_router rooms open user_id=%s", user_id)
                await _safe_query_edit(query, "Ошибка БД. Попробуйте /start.")
                return
            selected_raw = _normalize_to_list(prefs.get("rooms"))
            current_int = [int(x) for x in selected_raw if str(x).isdigit()]
            context.user_data["filter_draft_rooms"] = list(current_int)
            await _safe_query_edit(
                "Выберите комнаты (можно несколько):",
                reply_markup=_build_rooms_menu(current_int),
            )
            return
        if key == "district":
            context.user_data["await_filter_input"] = "district"
            await _safe_query_edit(
                "Введите один или несколько районов через запятую (сообщением в чат)."
            )
            return
        context.user_data["await_filter_input"] = key
        label = FILTER_KEYS.get(key, (key, str))[0]
        await _safe_query_edit(
            f"Введите значение для «{label}» ({key}) одним сообщением в чат."
        )
        return

    if data.startswith("cfgrooms:"):
        action = data.split(":")[1]
        current_int = context.user_data.get("filter_draft_rooms")
        if current_int is None:
            try:
                prefs = await asyncio.to_thread(get_user_preferences, user_id)
            except Exception:
                logger.exception("cfgrooms prefs user_id=%s", user_id)
                await _safe_query_edit(query, "Ошибка БД.")
                return
            current_int = [
                int(x) for x in _normalize_to_list(prefs.get("rooms")) if str(x).isdigit()
            ]
            context.user_data["filter_draft_rooms"] = list(current_int)
        if action == "clear":
            current_int = []
            context.user_data["filter_draft_rooms"] = []
            try:
                await _update_prefs_in_thread(user_id, {"rooms": []})
            except Exception:
                logger.exception("cfgrooms clear user_id=%s", user_id)
        else:
            value = int(action)
            if value in current_int:
                current_int.remove(value)
            else:
                current_int.append(value)
            current_int = sorted(set(current_int))
            context.user_data["filter_draft_rooms"] = list(current_int)
            try:
                await _update_prefs_in_thread(user_id, {"rooms": current_int})
            except Exception:
                logger.exception("cfgrooms toggle user_id=%s", user_id)
        await _safe_query_edit(
            "Выберите комнаты (можно несколько):",
            reply_markup=_build_rooms_menu(current_int),
        )
        return

    if data.startswith("cfgmetro:"):
        parts = data.split(":")
        action = parts[1]
        metros = _get_available_metro(context)
        selected = context.user_data.get("filter_draft_metro")
        if selected is None:
            try:
                prefs = await asyncio.to_thread(get_user_preferences, user_id)
            except Exception:
                logger.exception("cfgmetro prefs user_id=%s", user_id)
                await _safe_query_edit(query, "Ошибка БД.")
                return
            selected = _normalize_to_list(prefs.get("metro"))
            context.user_data["filter_draft_metro"] = list(selected)
        if action == "noop":
            return
        if action == "page":
            page = int(parts[2])
            await _safe_query_edit(
                "Выберите метро (можно несколько), затем «Сохранить»:",
                reply_markup=_build_metro_menu(metros, selected, page),
            )
            return
        if action == "toggle":
            page = int(parts[2])
            station_idx = int(parts[3])
            if station_idx < 0 or station_idx >= len(metros):
                await _safe_query_edit(
                    "Список метро обновился, выберите заново.",
                    reply_markup=_build_metro_menu(metros, selected, 0),
                )
                return
            station = metros[station_idx]
            sel_set = set(selected)
            if station in sel_set:
                sel_set.remove(station)
            else:
                sel_set.add(station)
            selected = sorted(sel_set)
            context.user_data["filter_draft_metro"] = list(selected)
            try:
                await _update_prefs_in_thread(user_id, {"metro": selected})
            except Exception:
                logger.exception("cfgmetro toggle user_id=%s", user_id)
            await _safe_query_edit(
                "Выберите метро (можно несколько), затем «Сохранить»:",
                reply_markup=_build_metro_menu(metros, selected, page),
            )
            return
        if action == "clear":
            selected = []
            context.user_data["filter_draft_metro"] = []
            try:
                await _update_prefs_in_thread(user_id, {"metro": []})
            except Exception:
                logger.exception("cfgmetro clear user_id=%s", user_id)
            await _safe_query_edit(
                "Выберите метро (можно несколько), затем «Сохранить»:",
                reply_markup=_build_metro_menu(metros, [], 0),
            )
            return
        if action == "save":
            context.user_data.pop("filter_draft_metro", None)
            await _safe_query_edit("Метро сохранено.", reply_markup=_build_filter_menu())
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


async def _on_bot_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирование и короткий ответ пользователю (иначе «тишина» после падения в хендлере)."""
    logger.exception("Необработанная ошибка в хендлере бота", exc_info=context.error)
    if not isinstance(update, Update):
        return
    text = "Произошла ошибка. Попробуйте ещё раз или /cancel — если бот ждал ввод фильтра."
    try:
        if update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(text)
        elif update.effective_message:
            await update.effective_message.reply_text(text)
    except Exception:
        logger.exception("Не удалось отправить сообщение об ошибке пользователю")


def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен")
        return

    init_bot_tables()
    # Последовательная обработка: иначе гонки по context.user_data (мастер фильтров + callback).
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .concurrent_updates(False)
        .build()
    )
    try:
        application.bot_data["metro_options"] = get_available_metro_stations(limit=500)
    except Exception as e:
        logger.warning("Не удалось загрузить список метро: %s", e)
        application.bot_data["metro_options"] = []

    application.add_error_handler(_on_bot_error)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_cmd))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("on", cmd_on))
    application.add_handler(CommandHandler("off", cmd_off))
    application.add_handler(CommandHandler("filters", filters_cmd))
    application.add_handler(CommandHandler("reset_filters", reset_filters_cmd))
    application.add_handler(CommandHandler("cancel", cancel_cmd))
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
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    main()
