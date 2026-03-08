"""
Планировщик задач для сканирования и отправки алертов.

Интеграция с app/scheduler/crontab.py для запуска 1-2 раза в день.
"""
import logging
import asyncio
from datetime import datetime
from telegram import Bot
from dotenv import dotenv_values
from pathlib import Path
import os

from .scanner import scan_new_offers
from .alert_logic import should_send_alert, prioritize_offers
from .templates import format_offer_message
from .database import (
    get_user, create_user, was_alert_sent, mark_alert_sent,
    reset_daily_alerts, SessionLocal, BotUser
)

logger = logging.getLogger(__name__)

# Загрузка токена
env_path = Path(__file__).parent.parent.parent / '.env'
env = dotenv_values(env_path)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or env.get('TELEGRAM_BOT_TOKEN')

# Интервал сканирования (часы)
SCAN_INTERVAL_HOURS = int(os.getenv('TELEGRAM_SCAN_INTERVAL_HOURS', '12') or env.get('TELEGRAM_SCAN_INTERVAL_HOURS', '12'))


async def send_alerts():
    """Основная функция отправки алертов."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен")
        return
    
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    try:
        # Сканирование новых объявлений
        logger.info(f"Сканирование новых объявлений за последние {SCAN_INTERVAL_HOURS} часов...")
        offers = scan_new_offers(hours=SCAN_INTERVAL_HOURS)
        
        if not offers:
            logger.info("Новых объявлений не найдено")
            return
        
        # Приоритизация
        offers = prioritize_offers(offers)
        
        # Получение всех активных пользователей
        session = SessionLocal()
        try:
            users = session.query(BotUser).filter(BotUser.is_active == True).all()
        finally:
            session.close()
        
        if not users:
            logger.info("Активных пользователей не найдено")
            return
        
        # Отправка алертов каждому пользователю
        for user in users:
            alerts_sent = 0
            
            for offer in offers:
                # Проверка, был ли уже отправлен алерт
                if was_alert_sent(user.user_id, offer['cian_id']):
                    continue
                
                # Проверка лимита
                if alerts_sent >= 5:  # Лимит 5 алертов в день
                    break
                
                # Получение предпочтений пользователя (можно расширить)
                user_preferences = {}
                # TODO: Парсинг preferences из JSON
                
                # Проверка, нужно ли отправлять алерт
                if should_send_alert(offer, user_preferences, user.alerts_today):
                    try:
                        message = format_offer_message(offer)
                        await bot.send_message(
                            chat_id=user.chat_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        
                        # Отметка об отправке
                        mark_alert_sent(user.user_id, offer['cian_id'])
                        
                        # Обновление счетчика
                        session = SessionLocal()
                        try:
                            db_user = session.query(BotUser).filter(BotUser.user_id == user.user_id).first()
                            if db_user:
                                db_user.alerts_today += 1
                                db_user.last_alert_time = datetime.now()
                                session.commit()
                        finally:
                            session.close()
                        
                        alerts_sent += 1
                        logger.info(f"Алерт отправлен пользователю {user.user_id} для объявления {offer['cian_id']}")
                        
                        # Задержка между сообщениями (чтобы не спамить)
                        await asyncio.sleep(1)
                    
                    except Exception as e:
                        logger.error(f"Ошибка при отправке алерта пользователю {user.user_id}: {e}")
        
        logger.info("Отправка алертов завершена")
    
    except Exception as e:
        logger.error(f"Ошибка при отправке алертов: {e}")
    finally:
        await bot.close()


def run_alert_job():
    """Запуск задачи отправки алертов (синхронная обертка для cron)."""
    asyncio.run(send_alerts())


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    run_alert_job()
