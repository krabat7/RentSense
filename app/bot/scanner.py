"""
Сканирование новых объявлений в БД с фильтрами и полями для предсказания.
"""
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import dotenv_values
from pathlib import Path
import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

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


def _row_to_offer(row) -> dict:
    """Преобразование строки запроса в словарь объявления."""
    return {
        'cian_id': row[0],
        'price': float(row[1]) if row[1] else 0.0,
        'publication_at': int(row[2]) if row[2] else None,
        'total_area': float(row[3]) if row[3] else None,
        'rooms_count': float(row[4]) if row[4] else None,
        'district': row[5],
        'street': row[6],
        'house': row[7],
        'metro': row[8],
        'travel_time': int(row[9]) if row[9] else None,
        'floor_number': int(row[10]) if row[10] else None,
        'floors_count': int(row[11]) if row[11] else None,
        'repair_type': row[12],
        'deal_type': row[13],
        'coordinates': row[14],
        'build_year': int(row[15]) if row[15] else None,
        'material_type': row[16],
        'living_area': float(row[17]) if row[17] else None,
        'kitchen_area': float(row[18]) if row[18] else None,
        'flat_type': row[19],
    }


def scan_new_offers(
    hours: int = 24,
    since_midnight: bool = False,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Сканирование новых объявлений за период с опциональными фильтрами.

    Args:
        hours: часов от текущего момента (если not since_midnight)
        since_midnight: если True — только с 00:00 сегодня
        filters: опционально district, rooms, area_min, area_max, price_min, price_max, metro, travel_time_max
        limit: макс. число объявлений

    Returns:
        Список объявлений с полями для predict (coordinates, build_year, material_type и т.д.)
    """
    try:
        if since_midnight:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_time = int(today.timestamp())
        else:
            cutoff_time = int((datetime.now() - timedelta(hours=hours)).timestamp())

        query = """
        SELECT 
            o.cian_id,
            o.price,
            o.publication_at,
            ri.total_area,
            ri.rooms_count,
            a.district,
            a.street,
            a.house,
            a.metro,
            a.travel_time,
            o.floor_number,
            o.floors_count,
            ri.repair_type,
            od.deal_type,
            a.coordinates,
            ro.build_year,
            ro.material_type,
            ri.living_area,
            ri.kitchen_area,
            od.flat_type
        FROM offers o
        LEFT JOIN addresses a ON o.cian_id = a.cian_id
        LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
        LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id
        LEFT JOIN offers_details od ON o.cian_id = od.cian_id
        WHERE o.publication_at >= :cutoff_time
        AND (od.deal_type IS NULL OR od.deal_type = 'rent')
        AND (o.category IS NULL OR o.category != 'dailyFlatRent')
        """
        params = {'cutoff_time': cutoff_time}

        if filters:
            if filters.get('district'):
                query += " AND a.district = :district"
                params['district'] = filters['district']
            if filters.get('rooms') is not None:
                query += " AND ri.rooms_count = :rooms"
                params['rooms'] = filters['rooms']
            if filters.get('area_min') is not None:
                query += " AND ri.total_area >= :area_min"
                params['area_min'] = filters['area_min']
            if filters.get('area_max') is not None:
                query += " AND ri.total_area <= :area_max"
                params['area_max'] = filters['area_max']
            if filters.get('price_min') is not None:
                query += " AND o.price >= :price_min"
                params['price_min'] = filters['price_min']
            if filters.get('price_max') is not None:
                query += " AND o.price <= :price_max"
                params['price_max'] = filters['price_max']
            if filters.get('metro'):
                query += " AND a.metro = :metro"
                params['metro'] = filters['metro']
            if filters.get('travel_time_max') is not None:
                query += " AND (a.travel_time IS NULL OR a.travel_time <= :travel_time_max)"
                params['travel_time_max'] = filters['travel_time_max']

        query += " ORDER BY o.publication_at DESC LIMIT :lim"
        params['lim'] = limit

        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.fetchall()
            offers = [_row_to_offer(r) for r in rows]

        logger.info(f"Найдено {len(offers)} объявлений (срез с {cutoff_time})")
        return offers

    except Exception as e:
        logger.error(f"Ошибка при сканировании объявлений: {e}")
        return []
