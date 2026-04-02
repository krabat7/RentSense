"""
Логика алертов: фильтрация по предпочтениям, приоритет по выгоде (прогноз − цена).
"""
import logging
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)

ALERT_LIMIT_PER_DAY = 5


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v is not None and str(v).strip() != ""]
    if isinstance(value, str) and "," in value:
        return [x.strip() for x in value.split(",") if x.strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [value]


def filter_offers_by_preferences(
    offers: List[Dict[str, Any]],
    user_preferences: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Оставляет только объявления, подходящие под предпочтения пользователя."""
    if not user_preferences:
        return list(offers)
    out = []
    districts = set(_as_list(user_preferences.get('district')))
    metros = set(_as_list(user_preferences.get('metro')))
    rooms_values = _as_list(user_preferences.get('rooms'))
    want_studio = False
    rooms_nums = set()
    for r in rooms_values:
        if r is None:
            continue
        s = str(r).strip().lower()
        if s in ("studio", "студия", "студ"):
            want_studio = True
            continue
        try:
            rooms_nums.add(int(r))
        except (TypeError, ValueError):
            continue
    for offer in offers:
        if user_preferences.get('price_max') is not None:
            if (offer.get('price') or 0) > user_preferences['price_max']:
                continue
        if user_preferences.get('price_min') is not None:
            if (offer.get('price') or 0) < user_preferences['price_min']:
                continue
        if districts:
            if offer.get('district') not in districts:
                continue
        if user_preferences.get('area_min') is not None:
            if (offer.get('total_area') or 0) < user_preferences['area_min']:
                continue
        if user_preferences.get('area_max') is not None:
            if (offer.get('total_area') or 0) > user_preferences['area_max']:
                continue
        if want_studio or rooms_nums:
            ft = (offer.get("flat_type") or "").strip().lower()
            is_studio = ft == "studio"
            try:
                offer_rooms = int(float(offer.get("rooms_count"))) if offer.get("rooms_count") is not None else None
            except (TypeError, ValueError):
                offer_rooms = None
            room_ok = False
            if want_studio and is_studio:
                room_ok = True
            for n in rooms_nums:
                if n == 1:
                    if offer_rooms == 1 and not is_studio:
                        room_ok = True
                elif offer_rooms == n:
                    room_ok = True
            if not room_ok:
                continue
        if metros:
            if offer.get('metro') not in metros:
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
    Объявления с predicted_price выше price. Сортировка по убыванию
    (predicted_price - price). В offer уже есть predicted_price.
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
    # predict_fn для первых 30 кандидатов, не отправленных ранее ([:30]).
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
    """Сортировка: новее и дешевле выше (без вызова предиктора)."""
    return sorted(
        offers,
        key=lambda x: (
            -(x.get('publication_at') or 0),
            x.get('price') or float('inf'),
        ),
    )
