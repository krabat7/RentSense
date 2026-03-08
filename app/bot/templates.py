"""
Шаблоны сообщений для форматирования объявлений.
"""


def format_offer_message(offer: dict) -> str:
    """
    Форматирование объявления в сообщение для Telegram.
    
    Args:
        offer: Словарь с данными объявления
    
    Returns:
        Отформатированное сообщение
    """
    price = offer.get('price', 0)
    total_area = offer.get('total_area')
    rooms_count = offer.get('rooms_count')
    district = offer.get('district', 'Не указан')
    street = offer.get('street', '')
    house = offer.get('house', '')
    metro = offer.get('metro', 'Не указано')
    travel_time = offer.get('travel_time')
    floor_number = offer.get('floor_number')
    floors_count = offer.get('floors_count')
    repair_type = offer.get('repair_type', 'Не указан')
    cian_id = offer.get('cian_id')
    
    # Формирование адреса
    address_parts = []
    if street:
        address_parts.append(street)
    if house:
        address_parts.append(house)
    address = ', '.join(address_parts) if address_parts else 'Адрес не указан'
    
    # Формирование информации о метро
    metro_info = metro
    if travel_time:
        metro_info += f" ({travel_time} мин)"
    
    # Формирование информации об этаже
    floor_info = ""
    if floor_number and floors_count:
        floor_info = f"{floor_number}/{floors_count} этаж"
    elif floor_number:
        floor_info = f"{floor_number} этаж"
    
    # Формирование сообщения
    message = f"🏠 *Новое объявление*\n\n"
    message += f"💰 *Цена:* {price:,.0f} руб\n"

    predicted_price = offer.get('predicted_price')
    if predicted_price is not None and predicted_price > 0:
        message += f"📊 *Прогноз модели:* {predicted_price:,.0f} руб\n"
        profit = offer.get('profit')
        if profit is not None and profit > 0:
            pct = (profit / price * 100) if price else 0
            message += f"✅ *Выгода:* +{profit:,.0f} руб (~{pct:.0f}%)\n"
    message += "\n"
    
    if total_area:
        message += f"📐 *Площадь:* {total_area:.1f} м²\n"
    
    if rooms_count:
        message += f"🚪 *Комнат:* {int(rooms_count)}\n"
    
    message += f"📍 *Район:* {district}\n"
    message += f"🏛 *Адрес:* {address}\n"
    
    if floor_info:
        message += f"🏢 *Этаж:* {floor_info}\n"
    
    message += f"🚇 *Метро:* {metro_info}\n"
    
    if repair_type and repair_type != 'Не указан':
        repair_names = {
            'euro': 'Евроремонт',
            'design': 'Дизайнерский',
            'cosmetic': 'Косметический',
            'no': 'Без ремонта'
        }
        repair_display = repair_names.get(repair_type, repair_type)
        message += f"🔨 *Ремонт:* {repair_display}\n"
    
    if cian_id:
        message += f"\n🔗 [Ссылка на Циан](https://www.cian.ru/rent/flat/{cian_id}/)\n"
    
    return message
