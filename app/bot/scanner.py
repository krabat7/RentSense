"""
Сканирование новых объявлений в БД.
"""
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import dotenv_values
from pathlib import Path
import os
import logging

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


def scan_new_offers(hours: int = 24) -> list:
    """
    Сканирование новых объявлений за последние N часов.
    
    Args:
        hours: Количество часов для сканирования
    
    Returns:
        Список новых объявлений
    """
    try:
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
            od.deal_type
        FROM offers o
        LEFT JOIN addresses a ON o.cian_id = a.cian_id
        LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
        LEFT JOIN offers_details od ON o.cian_id = od.cian_id
        WHERE o.publication_at >= :cutoff_time
        AND od.deal_type = 'rent'
        AND o.category != 'dailyFlatRent'
        ORDER BY o.publication_at DESC
        LIMIT 100
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(query), {'cutoff_time': cutoff_time})
            rows = result.fetchall()
            
            offers = []
            for row in rows:
                offers.append({
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
                    'deal_type': row[13]
                })
            
            logger.info(f"Найдено {len(offers)} новых объявлений за последние {hours} часов")
            return offers
    
    except Exception as e:
        logger.error(f"Ошибка при сканировании объявлений: {e}")
        return []
