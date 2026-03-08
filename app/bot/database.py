"""
База данных для Telegram бота.

Таблицы: bot_users, sent_alerts
"""
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from dotenv import dotenv_values
from pathlib import Path
import os

Base = declarative_base()


class BotUser(Base):
    """Пользователь бота."""
    __tablename__ = 'bot_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False)
    preferences = Column(Text, nullable=True)  # JSON с предпочтениями
    last_alert_time = Column(DateTime, nullable=True)
    alerts_today = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SentAlert(Base):
    """Отправленные алерты для дедупликации."""
    __tablename__ = 'sent_alerts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    cian_id = Column(BigInteger, nullable=False, index=True)
    sent_at = Column(DateTime, default=datetime.now, index=True)
    
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )


# Подключение к БД
env_path = Path(__file__).parent.parent.parent / '.env'
env = dotenv_values(env_path)

DBTYPE = os.getenv('DB_TYPE') or env.get('DB_TYPE') or 'mysql+pymysql'
LOGIN = os.getenv('DB_LOGIN') or env.get('DB_LOGIN') or 'root'
PASS = os.getenv('DB_PASS') or env.get('DB_PASS') or 'rootpassword'
IP = os.getenv('DB_IP') or env.get('DB_IP') or 'localhost'
PORT = os.getenv('DB_PORT') or env.get('DB_PORT') or '3307'
DBNAME = os.getenv('DB_NAME') or env.get('DB_NAME') or 'rentsense'

DATABASE_URL = f'{DBTYPE}://{LOGIN}:{PASS}@{IP}:{PORT}/{DBNAME}?charset=utf8mb4'
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def init_bot_tables():
    """Создание таблиц для бота."""
    Base.metadata.create_all(engine)


def get_user(user_id: int):
    """Получение пользователя из БД."""
    session = SessionLocal()
    try:
        return session.query(BotUser).filter(BotUser.user_id == user_id).first()
    finally:
        session.close()


def create_user(user_id: int, chat_id: int):
    """Создание нового пользователя."""
    session = SessionLocal()
    try:
        user = BotUser(user_id=user_id, chat_id=chat_id)
        session.add(user)
        session.commit()
        return user
    finally:
        session.close()


def was_alert_sent(user_id: int, cian_id: int) -> bool:
    """Проверка, был ли уже отправлен алерт для этого объявления."""
    session = SessionLocal()
    try:
        alert = session.query(SentAlert).filter(
            SentAlert.user_id == user_id,
            SentAlert.cian_id == cian_id
        ).first()
        return alert is not None
    finally:
        session.close()


def mark_alert_sent(user_id: int, cian_id: int):
    """Отметка о том, что алерт отправлен."""
    session = SessionLocal()
    try:
        alert = SentAlert(user_id=user_id, cian_id=cian_id)
        session.add(alert)
        session.commit()
    finally:
        session.close()


def reset_daily_alerts():
    """Сброс счетчика алертов за день (вызывается в начале нового дня)."""
    session = SessionLocal()
    try:
        session.query(BotUser).update({BotUser.alerts_today: 0})
        session.commit()
    finally:
        session.close()
