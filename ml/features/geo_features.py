"""
Географические фичи для модели предсказания цены аренды.

Расстояние до центра Москвы, расстояние до метро, кодирование района.
"""
import math
import pandas as pd


def calculate_distance_from_center(lat, lng, center_lat=55.753600, center_lng=37.621184):
    """Вычисление расстояния от точки до центра Москвы (формула гаверсинуса)."""
    earth_radius_km = 6371
    lat1, lng1, lat2, lng2 = map(math.radians, [lat, lng, center_lat, center_lng])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


def add_geo_features_v0(df):
    """Добавление географических фичей в датафрейм."""
    if 'coordinates' in df.columns:
        df['lat'] = df['coordinates'].apply(lambda x: x['lat'] if isinstance(x, dict) else None)
        df['lng'] = df['coordinates'].apply(lambda x: x['lng'] if isinstance(x, dict) else None)
        df['distance_from_center'] = df.apply(
            lambda row: calculate_distance_from_center(row['lat'], row['lng'])
            if pd.notna(row['lat']) and pd.notna(row['lng']) else None,
            axis=1
        )
    if 'travel_time' in df.columns:
        df['distance_to_metro'] = df['travel_time']
    if 'district' in df.columns:
        df['district_encoded'] = df['district']
    return df


