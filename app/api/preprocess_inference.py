"""Предобработка и фичи v2 для inference (те же трансформации, что при обучении)."""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from typing import Dict, Any

# Добавляем путь к ml модулю
sys.path.append(str(Path(__file__).parent.parent.parent / 'ml'))
from features import add_features_v2
from features.interaction_features import add_interaction_features
from features.geo_features import calculate_distance_from_center


def prepare_features_for_prediction(data: Dict[str, Any]) -> pd.DataFrame:
    """Применяет фичи v2 к данным квартиры, возвращает DataFrame с признаками."""
    # Создаем DataFrame из словаря
    df = pd.DataFrame([data])
    
    # Базовые фичи (нужны для других фичей)
    if 'total_area' in df.columns and 'price' in df.columns and pd.notna(df['price'].iloc[0]):
        df['total_area'] = pd.to_numeric(df['total_area'], errors='coerce')
        df['price_per_sqm'] = df['price'] / df['total_area']
    elif 'total_area' in df.columns:
        df['total_area'] = pd.to_numeric(df['total_area'], errors='coerce')
        df['price_per_sqm'] = None
    
    if 'build_year' in df.columns:
        df['build_year'] = pd.to_numeric(df['build_year'], errors='coerce')
        df['house_age'] = 2025 - df['build_year']
        df['house_age'] = df['house_age'].clip(lower=0, upper=300)
    
    # Применяем все фичи v2
    df = add_features_v2(df, use_clustering=False)  # Кластеризация требует много данных
    
    # Интеракции
    df = add_interaction_features(df)
    
    # Удаляем временные колонки, которые не нужны для модели
    exclude_cols = [
        'cian_id', 'price', 'price_changes', 'price_from_changes',
        'price_actual', 'publication_at', 'publication_date',
        'offer_created_at', 'offer_updated_at',
        'description', 'coordinates', 'lat', 'lng'
    ]
    
    for col in exclude_cols:
        if col in df.columns:
            df = df.drop(columns=[col])
    
    return df


def fill_missing_for_inference(df: pd.DataFrame, default_values: Dict[str, Any] = None) -> pd.DataFrame:
    """Заполнение пропусков значениями по умолчанию для inference."""
    if default_values is None:
        default_values = {
            'category': 'flatRent',
            'deal_type': 'rent',
            'repair_type': 'cosmetic',
            'material_type': 'panel',
            'realty_type': 'flat',
            'flat_type': 'rooms',
        }
    
    df = df.copy()
    
    # Заполняем числовые признаки нулями или медианой
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isna().any():
            df[col] = df[col].fillna(0)
    
    # Заполняем категориальные признаки
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        if df[col].isna().any():
            default_val = default_values.get(col, 'unknown')
            df[col] = df[col].fillna(default_val)
    
    return df
