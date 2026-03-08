"""
Сезонные фичи для модели предсказания цены аренды.

Извлечение временных признаков из даты публикации:
месяц, день недели, циклическое кодирование, агрегаты по сезону.
"""
import pandas as pd
import numpy as np
from datetime import datetime


def add_seasonal_features(df):
    """
    Добавление сезонных фичей в датафрейм.
    
    Создает фичи:
    - publication_month: месяц публикации (1-12)
    - publication_day_of_week: день недели (0=понедельник, 6=воскресенье)
    - is_weekend: выходной день (1) или рабочий (0)
    - publication_month_sin/cos: циклическое кодирование месяца
    - publication_day_sin/cos: циклическое кодирование дня недели
    """
    if 'publication_at' not in df.columns:
        return df
    
    df = df.copy()
    
    # Преобразуем publication_at в datetime
    df['publication_date'] = pd.to_datetime(df['publication_at'], unit='s', errors='coerce')
    
    # Извлекаем месяц (1-12)
    df['publication_month'] = df['publication_date'].dt.month
    
    # Извлекаем день недели (0=понедельник, 6=воскресенье)
    df['publication_day_of_week'] = df['publication_date'].dt.dayofweek
    
    # Бинарная фича: выходной день
    df['is_weekend'] = df['publication_day_of_week'].apply(
        lambda x: 1 if pd.notna(x) and x >= 5 else (0 if pd.notna(x) else None)
    )
    
    # Циклическое кодирование месяца (sin/cos для учета цикличности)
    # Месяц 1 (январь) и 12 (декабрь) должны быть близки
    df['publication_month_sin'] = df['publication_month'].apply(
        lambda x: np.sin(2 * np.pi * x / 12) if pd.notna(x) else None
    )
    df['publication_month_cos'] = df['publication_month'].apply(
        lambda x: np.cos(2 * np.pi * x / 12) if pd.notna(x) else None
    )
    
    # Циклическое кодирование дня недели
    df['publication_day_sin'] = df['publication_day_of_week'].apply(
        lambda x: np.sin(2 * np.pi * x / 7) if pd.notna(x) else None
    )
    df['publication_day_cos'] = df['publication_day_of_week'].apply(
        lambda x: np.cos(2 * np.pi * x / 7) if pd.notna(x) else None
    )
    
    # Сезон (весна, лето, осень, зима)
    def get_season(month):
        if pd.isna(month):
            return None
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'autumn'
    
    df['publication_season'] = df['publication_month'].apply(get_season)
    
    # Квартал года (1-4)
    df['publication_quarter'] = df['publication_date'].dt.quarter
    
    return df


def add_seasonal_aggregates(df, price_col='price_actual'):
    """
    Добавление агрегатов по сезону публикации.
    
    Вычисляет среднюю цену по месяцу/сезону за последний год.
    Требует наличия price_col в датафрейме.
    """
    if 'publication_date' not in df.columns or price_col not in df.columns:
        return df
    
    df = df.copy()
    
    # Агрегаты по месяцу
    monthly_avg = df.groupby('publication_month')[price_col].mean().to_dict()
    df['monthly_avg_price'] = df['publication_month'].map(monthly_avg)
    
    # Агрегаты по сезону
    if 'publication_season' in df.columns:
        seasonal_avg = df.groupby('publication_season')[price_col].mean().to_dict()
        df['seasonal_avg_price'] = df['publication_season'].map(seasonal_avg)
    
    # Агрегаты по кварталу
    if 'publication_quarter' in df.columns:
        quarterly_avg = df.groupby('publication_quarter')[price_col].mean().to_dict()
        df['quarterly_avg_price'] = df['publication_quarter'].map(quarterly_avg)
    
    return df
