"""
Планировщик: сканирование за сегодня, лучшие предложения по выгоде, 1 объявление за раз.
Запуск каждый час с 9 до 23; раз в день сообщение «нет новых объявлений» при необходимости.
"""
import logging
import asyncio
from datetime import datetime
from telegram import Bot
from dotenv import dotenv_values
from pathlib import Path
import os

from .scanner import scan_new_offers
from .alert_logic import get_best_offers_for_user
from .predict_client import get_predicted_price
from .templates import format_offer_message
from .database import (
    get_user,
    create_user,
    was_alert_sent,
    mark_alert_sent,
    get_sent_cian_ids,
    get_user_preferences,
    reset_daily_alerts,
    mark_no_offers_message_sent,
    should_send_no_offers_message,
    SessionLocal,
    BotUser,
)

logger = logging.getLogger(__name__)

env_path = Path(__file__).parent.parent.parent / '.env'
env = dotenv_values(env_path)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or env.get('TELEGRAM_BOT_TOKEN')

# Часы работы: с 9 до 23 включительно
ALERT_HOUR_START = 9
ALERT_HOUR_END = 23

# Только объявления за последние N часов — меньше шанс, что уже сняты с публикации
MAX_OFFER_AGE_HOURS = 12

NO_OFFERS_MESSAGE = (
    "За последние часы новых объявлений по вашим фильтрам не нашлось. "
    "Попробуйте расширить критерии: /filters и /set."
)


async def send_alerts():
    """Сканирует объявления за сегодня, по одному лучшему (по выгоде) на пользователя за запуск."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        # Объявления за последние MAX_OFFER_AGE_HOURS — свежие, реже сняты с публикации
        offers = scan_new_offers(hours=MAX_OFFER_AGE_HOURS, since_midnight=False, limit=200)
        if not offers:
            logger.info("Нет объявлений за последние %s ч", MAX_OFFER_AGE_HOURS)
            await _send_no_offers_if_needed(bot)
            return

        session = SessionLocal()
        try:
            users = session.query(BotUser).filter(BotUser.is_active == True).all()
        finally:
            session.close()

        if not users:
            logger.info("Нет активных пользователей")
            return

        for user in users:
            try:
                prefs = get_user_preferences(user.user_id)
                already_sent = get_sent_cian_ids(user.user_id)
                best = get_best_offers_for_user(
                    list(offers),
                    prefs if prefs else None,
                    already_sent,
                    get_predicted_price,
                    max_count=1,
                )
                if not best:
                    continue
                offer = best[0]
                message = format_offer_message(offer)
                await bot.send_message(
                    chat_id=user.chat_id,
                    text=message,
                    parse_mode='Markdown',
                )
                mark_alert_sent(user.user_id, offer['cian_id'])
                session = SessionLocal()
                try:
                    db_user = session.query(BotUser).filter(BotUser.user_id == user.user_id).first()
                    if db_user:
                        db_user.alerts_today += 1
                        db_user.last_alert_time = datetime.now()
                        session.commit()
                finally:
                    session.close()
                logger.info("Алерт отправлен user_id=%s cian_id=%s", user.user_id, offer['cian_id'])
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.exception("Ошибка при отправке алерта user_id=%s: %s", user.user_id, e)

        # В конце дня (23) отправить «нет новых» тем, кому за день ничего не пришло
        if datetime.now().hour >= ALERT_HOUR_END - 1:
            await _send_no_offers_if_needed(bot)
    except Exception as e:
        logger.exception("Ошибка при отправке алертов: %s", e)
    finally:
        await bot.close()


async def _send_no_offers_if_needed(bot: Bot):
    """Раз в день отправить сообщение «нет новых объявлений» активным пользователям с 0 алертов."""
    session = SessionLocal()
    try:
        users = session.query(BotUser).filter(BotUser.is_active == True).all()
    finally:
        session.close()
    for user in users:
        if not should_send_no_offers_message(user):
            continue
        try:
            await bot.send_message(chat_id=user.chat_id, text=NO_OFFERS_MESSAGE)
            mark_no_offers_message_sent(user.user_id)
            logger.info("Отправлено «нет новых» user_id=%s", user.user_id)
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning("Не удалось отправить «нет новых» user_id=%s: %s", user.user_id, e)


def run_alert_job():
    """Синхронная обертка для cron (каждый час с 9 до 23)."""
    asyncio.run(send_alerts())


def run_reset_daily():
    """Сброс счётчиков за день (запуск в 00:00)."""
    reset_daily_alerts()
    logger.info("Сброс алертов за день выполнен")


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
    )
    run_alert_job()
