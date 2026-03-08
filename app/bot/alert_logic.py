"""
Логика алертов: фильтрация по предпочтениям, приоритет по выгоде (прогноз − цена).
"""
import logging
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)

ALERT_LIMIT_PER_DAY = 5


def filter_offers_by_preferences(
    offers: List[Dict[str, Any]],
    user_preferences: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Оставляет только объявления, подходящие под предпочтения пользователя."""
    if not user_preferences:
        return list(offers)
    out = []
    for offer in offers:
        if user_preferences.get('price_max') is not None:
            if (offer.get('price') or 0) > user_preferences['price_max']:
                continue
        if user_preferences.get('price_min') is not None:
            if (offer.get('price') or 0) < user_preferences['price_min']:
                continue
        if user_preferences.get('district'):
            if offer.get('district') != user_preferences['district']:
                continue
        if user_preferences.get('area_min') is not None:
            if (offer.get('total_area') or 0) < user_preferences['area_min']:
                continue
        if user_preferences.get('area_max') is not None:
            if (offer.get('total_area') or 0) > user_preferences['area_max']:
                continue
        if user_preferences.get('rooms') is not None:
            if offer.get('rooms_count') != user_preferences['rooms']:
                continue
        if user_preferences.get('metro'):
            if offer.get('metro') != user_preferences['metro']:
                continue
        if user_preferences.get('travel_time_max') is not None:
            t = offer.get('travel_time')
            if t is not None and t > user_preferences['travel_time_max']:
                continue
        out.append(offer)
    return out


def should_send_alert(
    offer: Dict[str, Any],
    user_preferences: Optional[Dict[str, Any]] = None,
    alerts_today: int = 0,
) -> bool:
    """Проверка: лимит не превышен и объявление подходит под предпочтения."""
    if alerts_today >= ALERT_LIMIT_PER_DAY:
        return False
    filtered = filter_offers_by_preferences([offer], user_preferences)
    return len(filtered) > 0


def prioritize_by_profit(
    offers: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Оставляет объявления, где предсказанная цена выше реальной;
    сортирует по убыванию выгоды (predicted_price - price).
    Ожидает, что у каждого offer уже есть ключ predicted_price.
    """
    with_profit = [
        o for o in offers
        if o.get('predicted_price') is not None
        and (o['predicted_price'] > (o.get('price') or 0))
    ]
    for o in with_profit:
        o['profit'] = o['predicted_price'] - (o.get('price') or 0)
    return sorted(with_profit, key=lambda x: -x['profit'])


def get_best_offers_for_user(
    offers: List[Dict[str, Any]],
    user_preferences: Optional[Dict[str, Any]],
    already_sent_cian_ids: set,
    predict_fn: Callable[[Dict[str, Any]], Optional[float]],
    max_count: int = 1,
) -> List[Dict[str, Any]]:
    """
    Фильтрует по предпочтениям, добавляет predicted_price, оставляет только выгодные,
    сортирует по убыванию выгоды, исключает уже отправленные, возвращает до max_count штук.
    """
    filtered = filter_offers_by_preferences(offers, user_preferences)
    # Ограничиваем число запросов к predict (например первые 30 по новизне)
    to_predict = [o for o in filtered if o.get('cian_id') not in already_sent_cian_ids][:30]
    for o in to_predict:
        if o.get('predicted_price') is None:
            o['predicted_price'] = predict_fn(o)
    prioritized = prioritize_by_profit(to_predict)
    result = []
    for o in prioritized:
        if o['cian_id'] in already_sent_cian_ids:
            continue
        if len(result) >= max_count:
            break
        result.append(o)
    return result


def prioritize_offers(offers: list) -> list:
    """
    Устаревшая приоритизация (только по новизне и цене).
    Для новых алертов используется get_best_offers_for_user с predict.
    """
    return sorted(
        offers,
        key=lambda x: (
            -(x.get('publication_at') or 0),
            x.get('price') or float('inf'),
        ),
    )
