"""
Клиент для вызова API предсказания цены по объявлению.
"""
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import requests
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

env_path = Path(__file__).parent.parent.parent / '.env'
env = dotenv_values(env_path)
API_BASE_URL = (
    os.getenv('API_BASE_URL') or env.get('API_BASE_URL') or 'http://localhost:8000'
).rstrip('/')


def _offer_to_predict_payload(offer: Dict[str, Any]) -> Dict[str, Any]:
    """Собирает тело запроса для POST /api/predict из словаря объявления."""
    cian_id = offer.get('cian_id') or 0
    price = float(offer.get('price') or 0)
    coordinates = offer.get('coordinates')
    if isinstance(coordinates, str):
        try:
            import json
            coordinates = json.loads(coordinates) if coordinates else None
        except Exception:
            coordinates = None
    payload = {
        'cian_id': cian_id,
        'price': price,
        'category': 'flatRent',
        'views_count': None,
        'photos_count': None,
        'floor_number': offer.get('floor_number'),
        'floors_count': offer.get('floors_count'),
        'publication_at': offer.get('publication_at'),
        'county': None,
        'district': offer.get('district'),
        'street': offer.get('street'),
        'house': offer.get('house'),
        'metro': offer.get('metro'),
        'travel_type': None,
        'travel_time': offer.get('travel_time'),
        'coordinates': coordinates,
        'repair_type': offer.get('repair_type') or 'cosmetic',
        'total_area': offer.get('total_area'),
        'living_area': offer.get('living_area'),
        'kitchen_area': offer.get('kitchen_area'),
        'ceiling_height': None,
        'balconies': 0,
        'loggias': 0,
        'rooms_count': offer.get('rooms_count'),
        'separated_wc': 0,
        'combined_wc': 0,
        'windows_view': None,
        'build_year': offer.get('build_year'),
        'entrances': None,
        'material_type': offer.get('material_type') or 'panel',
        'parking_type': None,
        'garbage_chute': False,
        'lifts_count': None,
        'passenger_lifts': 0,
        'cargo_lifts': None,
        'realty_type': 'flat',
        'project_type': None,
        'heat_type': None,
        'gas_type': None,
        'is_apartment': False,
        'is_penthouse': False,
        'is_mortgage_allowed': False,
        'is_premium': False,
        'is_emergency': False,
        'renovation_programm': False,
        'finish_date': None,
        'agent_name': None,
        'deal_type': offer.get('deal_type') or 'rent',
        'flat_type': offer.get('flat_type') or 'rooms',
        'sale_type': None,
        'description': None,
        'name': None,
        'review_count': None,
        'total_rate': None,
        'buildings_count': None,
        'foundation_year': None,
        'is_reliable': None,
    }
    return payload


def get_predicted_price(offer: Dict[str, Any], timeout: int = 15) -> Optional[float]:
    """
    Запрос предсказанной цены для объявления через POST /api/predict.

    Returns:
        Предсказанная цена (P50) или None при ошибке.
    """
    url = f'{API_BASE_URL}/api/predict'
    try:
        payload = _offer_to_predict_payload(offer)
        body = {'id': str(offer.get('cian_id', '')), 'data': payload, 'sysmodel': 'catboost'}
        resp = requests.post(url, json=body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return float(data.get('price', 0))
    except Exception as e:
        logger.warning('Predict failed for cian_id=%s: %s', offer.get('cian_id'), e)
        return None
