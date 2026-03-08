"""
Логика определения, нужно ли отправлять алерт пользователю.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Лимиты
ALERT_LIMIT_PER_DAY = 5


def should_send_alert(offer: Dict[str, Any], user_preferences: Optional[Dict[str, Any]] = None,
                     alerts_today: int = 0) -> bool:
    """
    Проверка, нужно ли отправлять алерт пользователю.
    
    Args:
        offer: Объявление
        user_preferences: Предпочтения пользователя (цена мин/макс, район, площадь и т.д.)
        alerts_today: Количество алертов, отправленных сегодня
    
    Returns:
        True, если нужно отправить алерт
    """
    # Проверка лимита
    if alerts_today >= ALERT_LIMIT_PER_DAY:
        return False
    
    # Если нет предпочтений, отправляем все
    if not user_preferences:
        return True
    
    # Фильтры по предпочтениям
    if 'price_max' in user_preferences:
        if offer.get('price', 0) > user_preferences['price_max']:
            return False
    
    if 'price_min' in user_preferences:
        if offer.get('price', 0) < user_preferences['price_min']:
            return False
    
    if 'district' in user_preferences and user_preferences['district']:
        if offer.get('district') != user_preferences['district']:
            return False
    
    if 'area_min' in user_preferences:
        if offer.get('total_area', 0) < user_preferences['area_min']:
            return False
    
    if 'area_max' in user_preferences:
        if offer.get('total_area', 0) > user_preferences['area_max']:
            return False
    
    if 'rooms' in user_preferences:
        if offer.get('rooms_count') != user_preferences['rooms']:
            return False
    
    return True


def prioritize_offers(offers: list) -> list:
    """
    Приоритизация объявлений для отправки.
    
    Приоритет:
    1. Новые объявления (по publication_at)
    2. Дешевые (по цене)
    3. В хороших районах (можно добавить рейтинг районов)
    
    Args:
        offers: Список объявлений
    
    Returns:
        Отсортированный список
    """
    # Сортируем по приоритету: сначала новые, потом дешевые
    sorted_offers = sorted(
        offers,
        key=lambda x: (
            -x.get('publication_at', 0),  # Новые сначала (по убыванию timestamp)
            x.get('price', float('inf'))  # Дешевые сначала
        )
    )
    
    return sorted_offers
