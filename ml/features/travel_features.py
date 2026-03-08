"""
Travel-time фичи для модели предсказания цены аренды.

Улучшенная обработка travel_time: разделение на walking/transport,
категоризация по зонам доступности метро.
"""
import pandas as pd
import numpy as np


def add_travel_features(df):
    """
    Добавление travel-time фичей в датафрейм.
    
    Создает фичи:
    - metro_walking_time: время пешком до метро (если travel_type='walking')
    - metro_transport_time: время на транспорте до метро (если travel_type='transport')
    - has_metro_nearby: есть ли метро рядом (< 10 мин)
    - metro_accessibility_zone: зона доступности метро (0-5, 5-10, 10-15, >15 мин)
    """
    if 'travel_time' not in df.columns:
        return df
    
    df = df.copy()
    
    # Преобразуем travel_time в числовой формат
    df['travel_time'] = pd.to_numeric(df['travel_time'], errors='coerce')
    
    # Разделение на walking и transport время
    if 'travel_type' in df.columns:
        # Если travel_type='walking', то это время пешком
        df['metro_walking_time'] = df.apply(
            lambda row: row['travel_time'] if pd.notna(row['travel_time']) and 
            str(row.get('travel_type', '')).lower() == 'walking' else None,
            axis=1
        )
        
        # Если travel_type='transport' или другой, то это время на транспорте
        df['metro_transport_time'] = df.apply(
            lambda row: row['travel_time'] if pd.notna(row['travel_time']) and 
            str(row.get('travel_type', '')).lower() != 'walking' else None,
            axis=1
        )
    else:
        # Если travel_type отсутствует, предполагаем что это общее время
        # Разделяем поровну или используем как walking_time
        df['metro_walking_time'] = df['travel_time']
        df['metro_transport_time'] = None
    
    # Бинарная фича: есть ли метро рядом (< 10 минут)
    df['has_metro_nearby'] = df['travel_time'].apply(
        lambda x: 1 if pd.notna(x) and x < 10 else (0 if pd.notna(x) else None)
    )
    
    # Категоризация по зонам доступности метро
    def categorize_metro_zone(travel_time):
        if pd.isna(travel_time):
            return None
        if travel_time <= 5:
            return '0-5'
        elif travel_time <= 10:
            return '5-10'
        elif travel_time <= 15:
            return '10-15'
        else:
            return '15+'
    
    df['metro_accessibility_zone'] = df['travel_time'].apply(categorize_metro_zone)
    
    # Дополнительные фичи для лучшей категоризации
    # Расстояние до метро (приблизительно, если нет точных данных)
    # Средняя скорость пешком ~5 км/ч, на транспорте ~30 км/ч
    if 'travel_type' in df.columns:
        df['estimated_distance_to_metro_km'] = df.apply(
            lambda row: (
                row['travel_time'] / 60 * 5 if str(row.get('travel_type', '')).lower() == 'walking'
                else row['travel_time'] / 60 * 30 if pd.notna(row['travel_time'])
                else None
            ),
            axis=1
        )
    else:
        # По умолчанию считаем пешком
        df['estimated_distance_to_metro_km'] = df['travel_time'].apply(
            lambda x: x / 60 * 5 if pd.notna(x) else None
        )
    
    return df
