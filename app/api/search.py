"""
Endpoint для поиска объявлений в БД с фильтрами и пагинацией.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from dotenv import dotenv_values
from pathlib import Path
import os

router = APIRouter()

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


class OfferItem(BaseModel):
    """Элемент объявления в результатах поиска."""
    cian_id: int
    price: float
    total_area: Optional[float] = None
    rooms_count: Optional[float] = None
    district: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = None
    metro: Optional[str] = None
    travel_time: Optional[int] = None
    floor_number: Optional[int] = None
    floors_count: Optional[int] = None
    repair_type: Optional[str] = None
    publication_at: Optional[int] = None


class SearchResponse(BaseModel):
    """Ответ на запрос поиска."""
    total: int
    page: int
    limit: int
    results: List[OfferItem]


@router.get('/search', response_model=SearchResponse)
async def search_offers(
    district: Optional[str] = Query(None, description="Район"),
    price_min: Optional[float] = Query(None, description="Минимальная цена"),
    price_max: Optional[float] = Query(None, description="Максимальная цена"),
    area_min: Optional[float] = Query(None, description="Минимальная площадь"),
    area_max: Optional[float] = Query(None, description="Максимальная площадь"),
    rooms: Optional[int] = Query(None, description="Количество комнат"),
    metro: Optional[str] = Query(None, description="Станция метро"),
    travel_time_max: Optional[int] = Query(None, description="Максимальное время до метро (мин)"),
    sort_by: str = Query('relevance', description="Сортировка: relevance, price_asc, price_desc, date_desc"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(20, ge=1, le=100, description="Количество результатов на странице")
):
    """
    Поиск объявлений с фильтрами и пагинацией.
    
    Параметры:
    - district: фильтр по району
    - price_min/max: фильтр по цене
    - area_min/max: фильтр по площади
    - rooms: фильтр по количеству комнат
    - metro: фильтр по метро
    - travel_time_max: максимальное время до метро
    - sort_by: сортировка (relevance, price_asc, price_desc, date_desc)
    - page: номер страницы (начиная с 1)
    - limit: количество результатов на странице (1-100)
    
    Returns:
        SearchResponse с результатами поиска
    """
    try:
        # Построение SQL запроса
        query = """
        SELECT 
            o.cian_id,
            o.price,
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
            o.publication_at
        FROM offers o
        LEFT JOIN addresses a ON o.cian_id = a.cian_id
        LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
        LEFT JOIN offers_details od ON o.cian_id = od.cian_id
        WHERE 1=1
        """
        
        params = {}
        
        # Фильтры
        if district:
            query += " AND a.district = :district"
            params['district'] = district
        
        if price_min is not None:
            query += " AND o.price >= :price_min"
            params['price_min'] = price_min
        
        if price_max is not None:
            query += " AND o.price <= :price_max"
            params['price_max'] = price_max
        
        if area_min is not None:
            query += " AND ri.total_area >= :area_min"
            params['area_min'] = area_min
        
        if area_max is not None:
            query += " AND ri.total_area <= :area_max"
            params['area_max'] = area_max
        
        if rooms is not None:
            query += " AND ri.rooms_count = :rooms"
            params['rooms'] = rooms
        
        if metro:
            query += " AND a.metro LIKE :metro"
            params['metro'] = f"%{metro}%"
        
        if travel_time_max is not None:
            query += " AND a.travel_time <= :travel_time_max"
            params['travel_time_max'] = travel_time_max
        
        # Фильтр только аренды
        query += " AND od.deal_type = 'rent'"
        query += " AND o.category != 'dailyFlatRent'"
        
        # Подсчет общего количества
        count_query = f"SELECT COUNT(*) as total FROM ({query}) as filtered"
        
        # Сортировка
        if sort_by == 'price_asc':
            query += " ORDER BY o.price ASC"
        elif sort_by == 'price_desc':
            query += " ORDER BY o.price DESC"
        elif sort_by == 'date_desc':
            query += " ORDER BY o.publication_at DESC"
        else:  # relevance (по умолчанию)
            query += " ORDER BY o.publication_at DESC, o.price ASC"
        
        # Пагинация
        offset = (page - 1) * limit
        query += " LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        # Выполнение запросов
        with engine.connect() as conn:
            # Подсчет общего количества
            count_result = conn.execute(text(count_query), params)
            total = count_result.fetchone()[0]
            
            # Получение результатов
            result = conn.execute(text(query), params)
            rows = result.fetchall()
            
            # Преобразование в список словарей
            results = []
            for row in rows:
                results.append({
                    'cian_id': row[0],
                    'price': float(row[1]) if row[1] else 0.0,
                    'total_area': float(row[2]) if row[2] else None,
                    'rooms_count': float(row[3]) if row[3] else None,
                    'district': row[4],
                    'street': row[5],
                    'house': row[6],
                    'metro': row[7],
                    'travel_time': int(row[8]) if row[8] else None,
                    'floor_number': int(row[9]) if row[9] else None,
                    'floors_count': int(row[10]) if row[10] else None,
                    'repair_type': row[11],
                    'publication_at': int(row[12]) if row[12] else None
                })
        
        return SearchResponse(
            total=total,
            page=page,
            limit=limit,
            results=[OfferItem(**item) for item in results]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Ошибка при поиске: {str(e)}')
