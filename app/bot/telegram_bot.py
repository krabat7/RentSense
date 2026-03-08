"""
Telegram бот для отправки алертов о новых объявлениях.

Команды: /start, /help, /status
"""
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import dotenv_values
from pathlib import Path

from .database import init_bot_tables

logger = logging.getLogger(__name__)

# Загрузка токена из .env
env_path = Path(__file__).parent.parent.parent / '.env'
env = dotenv_values(env_path)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or env.get('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    await update.message.reply_text(
        "Привет! Я бот RentSense.\n\n"
        "Я буду отправлять вам уведомления о новых объявлениях на аренду квартир.\n\n"
        "Команды:\n"
        "/help - справка\n"
        "/status - статус подписки"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help."""
    await update.message.reply_text(
        "Справка по командам:\n\n"
        "/start - начать работу с ботом\n"
        "/help - показать эту справку\n"
        "/status - проверить статус подписки\n\n"
        "Бот отправляет до 5 уведомлений в день о новых объявлениях, "
        "которые соответствуют вашим критериям."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status."""
    user_id = update.effective_user.id
    
    # TODO: Проверка статуса из БД
    await update.message.reply_text(
        f"Ваш ID: {user_id}\n"
        "Статус: Активен\n"
        "Уведомлений сегодня: 0/5"
    )


def main():
    """Запуск бота."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен")
        return
    
    init_bot_tables()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    
    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    main()
