"""
Фичи этажности и типа дома для модели предсказания цены аренды.

Извлечение признаков из floor_number и floors_count:
соотношение этажей, позиция на этаже, категория типа дома.
"""
import pandas as pd
import numpy as np


def add_building_features(df):
    """
    Добавление фичей этажности и типа дома в датафрейм.
    
    Создает фичи:
    - floor_ratio: соотношение этажа к общему количеству этажей
    - is_first_floor: первый этаж (1) или нет (0)
    - is_last_floor: последний этаж (1) или нет (0)
    - is_middle_floor: средний этаж (1) или нет (0)
    - building_type_category: категория дома (низкоэтажный, среднеэтажный, высокоэтажный)
    - material_floor_interaction: взаимодействие материала и этажа
    """
    df = df.copy()
    
    # Преобразуем в числовой формат
    df['floor_number'] = pd.to_numeric(df['floor_number'], errors='coerce')
    df['floors_count'] = pd.to_numeric(df['floors_count'], errors='coerce')
    
    # Соотношение этажа к общему количеству этажей
    df['floor_ratio'] = df.apply(
        lambda row: (
            row['floor_number'] / row['floors_count']
            if pd.notna(row['floor_number']) and pd.notna(row['floors_count']) and row['floors_count'] > 0
            else None
        ),
        axis=1
    )
    
    # Бинарные фичи: первый, последний, средний этаж
    df['is_first_floor'] = df.apply(
        lambda row: (
            1 if pd.notna(row['floor_number']) and row['floor_number'] == 1
            else (0 if pd.notna(row['floor_number']) else None)
        ),
        axis=1
    )
    
    df['is_last_floor'] = df.apply(
        lambda row: (
            1 if pd.notna(row['floor_number']) and pd.notna(row['floors_count']) and
            row['floor_number'] == row['floors_count']
            else (0 if pd.notna(row['floor_number']) and pd.notna(row['floors_count']) else None)
        ),
        axis=1
    )
    
    df['is_middle_floor'] = df.apply(
        lambda row: (
            1 if pd.notna(row['floor_number']) and pd.notna(row['floors_count']) and
            row['floors_count'] > 2 and 1 < row['floor_number'] < row['floors_count']
            else (0 if pd.notna(row['floor_number']) and pd.notna(row['floors_count']) else None)
        ),
        axis=1
    )
    
    # Категория типа дома по количеству этажей
    def categorize_building_type(floors_count):
        if pd.isna(floors_count):
            return None
        if floors_count < 5:
            return 'low-rise'  # Низкоэтажный
        elif floors_count <= 12:
            return 'mid-rise'  # Среднеэтажный
        else:
            return 'high-rise'  # Высокоэтажный
    
    df['building_type_category'] = df['floors_count'].apply(categorize_building_type)
    
    # Взаимодействие материала и этажа
    if 'material_type' in df.columns:
        df['material_floor_interaction'] = df.apply(
            lambda row: (
                f"{row.get('material_type', 'unknown')}_{row.get('building_type_category', 'unknown')}"
                if pd.notna(row.get('floors_count'))
                else None
            ),
            axis=1
        )
    else:
        df['material_floor_interaction'] = None
    
    # Дополнительные фичи: относительная позиция на этаже
    # 0.0 = первый этаж, 1.0 = последний этаж
    df['floor_position_normalized'] = df.apply(
        lambda row: (
            (row['floor_number'] - 1) / (row['floors_count'] - 1)
            if pd.notna(row['floor_number']) and pd.notna(row['floors_count']) and
            row['floors_count'] > 1
            else None
        ),
        axis=1
    )
    
    # Фича: этаж в нижней трети, средней трети или верхней трети
    def get_floor_third(floor_number, floors_count):
        if pd.isna(floor_number) or pd.isna(floors_count) or floors_count == 0:
            return None
        third = floors_count / 3
        if floor_number <= third:
            return 'bottom'
        elif floor_number <= 2 * third:
            return 'middle'
        else:
            return 'top'
    
    df['floor_third'] = df.apply(
        lambda row: get_floor_third(row['floor_number'], row['floors_count']),
        axis=1
    )
    
    return df
