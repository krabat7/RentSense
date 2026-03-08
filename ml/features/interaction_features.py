"""
Интеракции (interactions) фичи для модели предсказания цены аренды.

Полиномиальные фичи, комбинации признаков, отношения между признаками.
"""
import pandas as pd
import numpy as np


def add_interaction_features(df):
    """
    Добавление интеракций в датафрейм.
    
    Создает фичи:
    - Полиномиальные: total_area^2, rooms_count^2
    - Комбинации: rooms_count * total_area, price_per_sqm * district
    - Отношения: living_area / total_area, kitchen_area / total_area
    """
    df = df.copy()
    
    # Полиномиальные фичи
    if 'total_area' in df.columns:
        df['total_area'] = pd.to_numeric(df['total_area'], errors='coerce')
        df['total_area_squared'] = df['total_area'] ** 2
    
    if 'rooms_count' in df.columns:
        df['rooms_count'] = pd.to_numeric(df['rooms_count'], errors='coerce')
        df['rooms_count_squared'] = df['rooms_count'] ** 2
    
    if 'kitchen_area' in df.columns:
        df['kitchen_area'] = pd.to_numeric(df['kitchen_area'], errors='coerce')
        df['kitchen_area_squared'] = df['kitchen_area'] ** 2
    
    # Комбинации числовых признаков
    if 'rooms_count' in df.columns and 'total_area' in df.columns:
        df['rooms_area_interaction'] = df['rooms_count'] * df['total_area']
    
    if 'living_area' in df.columns and 'total_area' in df.columns:
        df['living_total_interaction'] = df['living_area'] * df['total_area']
    
    if 'kitchen_area' in df.columns and 'total_area' in df.columns:
        df['kitchen_total_interaction'] = df['kitchen_area'] * df['total_area']
    
    # Отношения (ratios)
    if 'living_area' in df.columns and 'total_area' in df.columns:
        df['living_area_ratio'] = df.apply(
            lambda row: (
                row['living_area'] / row['total_area']
                if pd.notna(row['living_area']) and pd.notna(row['total_area']) and row['total_area'] > 0
                else None
            ),
            axis=1
        )
    
    if 'kitchen_area' in df.columns and 'total_area' in df.columns:
        df['kitchen_area_ratio'] = df.apply(
            lambda row: (
                row['kitchen_area'] / row['total_area']
                if pd.notna(row['kitchen_area']) and pd.notna(row['total_area']) and row['total_area'] > 0
                else None
            ),
            axis=1
        )
    
    # Комбинации с price_per_sqm (если есть)
    if 'price_per_sqm' in df.columns:
        if 'district' in df.columns:
            # Создаем категориальную фичу для взаимодействия
            df['price_sqm_district_interaction'] = df.apply(
                lambda row: (
                    f"{row.get('price_per_sqm', 0):.0f}_{row.get('district', 'unknown')}"
                    if pd.notna(row.get('price_per_sqm')) and pd.notna(row.get('district'))
                    else None
                ),
                axis=1
            )
        
        if 'repair_type' in df.columns:
            df['price_sqm_repair_interaction'] = df.apply(
                lambda row: (
                    f"{row.get('price_per_sqm', 0):.0f}_{row.get('repair_type', 'unknown')}"
                    if pd.notna(row.get('price_per_sqm')) and pd.notna(row.get('repair_type'))
                    else None
                ),
                axis=1
            )
    
    # Комбинации total_area с категориальными признаками
    if 'total_area' in df.columns:
        if 'repair_type' in df.columns:
            df['area_repair_interaction'] = df.apply(
                lambda row: (
                    f"{row.get('total_area', 0):.0f}_{row.get('repair_type', 'unknown')}"
                    if pd.notna(row.get('total_area')) and pd.notna(row.get('repair_type'))
                    else None
                ),
                axis=1
            )
        
        if 'material_type' in df.columns:
            df['area_material_interaction'] = df.apply(
                lambda row: (
                    f"{row.get('total_area', 0):.0f}_{row.get('material_type', 'unknown')}"
                    if pd.notna(row.get('total_area')) and pd.notna(row.get('material_type'))
                    else None
                ),
                axis=1
            )
    
    # Комбинации с floor_number
    if 'floor_number' in df.columns and 'total_area' in df.columns:
        df['floor_area_interaction'] = df['floor_number'] * df['total_area']
    
    if 'floor_number' in df.columns and 'rooms_count' in df.columns:
        df['floor_rooms_interaction'] = df['floor_number'] * df['rooms_count']
    
    # Комбинации с build_year
    if 'build_year' in df.columns:
        df['build_year'] = pd.to_numeric(df['build_year'], errors='coerce')
        if 'total_area' in df.columns:
            df['year_area_interaction'] = df['build_year'] * df['total_area']
    
    # Комбинации с distance_from_center (если есть)
    if 'distance_from_center' in df.columns:
        if 'total_area' in df.columns:
            df['distance_area_interaction'] = df['distance_from_center'] * df['total_area']
        
        if 'price_per_sqm' in df.columns:
            df['distance_price_sqm_interaction'] = df['distance_from_center'] * df['price_per_sqm']
    
    return df
