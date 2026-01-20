"""
Скрипт подготовки данных для обучения моделей.

Загрузка данных из БД, фильтрация, очистка выбросов,
feature engineering, заполнение пропусков, временное разделение train/test.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from dotenv import dotenv_values

sys.path.append(str(Path(__file__).parent))
from features.geo_features import add_geo_features_v0


def load_data_from_db(engine):
    """Загрузка данных из БД"""
    query = """
    SELECT 
        o.cian_id,
        o.price,
        o.price_changes,
        o.category,
        o.views_count,
        o.photos_count,
        o.floor_number,
        o.floors_count,
        o.publication_at,
        o.created_at as offer_created_at,
        o.updated_at as offer_updated_at,
        
        a.county,
        a.district,
        a.street,
        a.house,
        a.metro,
        a.travel_type,
        a.travel_time,
        a.coordinates,
        
        ri.repair_type,
        ri.total_area,
        ri.living_area,
        ri.kitchen_area,
        ri.ceiling_height,
        ri.balconies,
        ri.loggias,
        ri.rooms_count,
        ri.separated_wc,
        ri.combined_wc,
        ri.windows_view,
        
        ro.build_year,
        ro.entrances,
        ro.material_type,
        ro.parking_type,
        ro.garbage_chute,
        ro.lifts_count,
        ro.passenger_lifts,
        ro.cargo_lifts,
        
        rd.realty_type,
        rd.project_type,
        rd.heat_type,
        rd.gas_type,
        rd.is_apartment,
        rd.is_penthouse,
        rd.is_mortgage_allowed,
        rd.is_premium,
        rd.is_emergency,
        
        od.deal_type,
        od.flat_type,
        od.payment_period,
        od.deposit,
        od.prepay_months,
        od.utilities_included,
        od.client_fee,
        od.agent_fee,
        od.description,
        
        d.name as developer_name,
        d.review_count as developer_review_count,
        d.total_rate as developer_rate,
        d.buildings_count as developer_buildings_count,
        d.foundation_year as developer_foundation_year,
        d.is_reliable as developer_is_reliable
    FROM offers o
    LEFT JOIN addresses a ON o.cian_id = a.cian_id
    LEFT JOIN realty_inside ri ON o.cian_id = ri.cian_id
    LEFT JOIN realty_outside ro ON o.cian_id = ro.cian_id
    LEFT JOIN realty_details rd ON o.cian_id = rd.cian_id
    LEFT JOIN offers_details od ON o.cian_id = od.cian_id
    LEFT JOIN developers d ON o.cian_id = d.cian_id
    """
    
    print("Загрузка данных из БД...")
    df = pd.read_sql(query, engine)
    print(f"Загружено строк: {len(df)}")
    return df


def get_latest_price_from_changes(price_changes_json):
    """Извлекает последнюю цену из price_changes по дате changeTime"""
    if not price_changes_json:
        return None
    try:
        if isinstance(price_changes_json, str):
            changes = json.loads(price_changes_json)
        else:
            changes = price_changes_json
            
        if not isinstance(changes, list) or len(changes) == 0:
            return None
        
        sorted_changes = sorted(
            changes, 
            key=lambda x: x.get('changeTime', ''),
            reverse=True
        )
        
        latest = sorted_changes[0]
        return latest.get('priceData', {}).get('price')
    except Exception:
        return None


def add_price_actual(df):
    """Добавляет актуальную цену из price_changes"""
    if 'price_changes' in df.columns:
        df['price_from_changes'] = df['price_changes'].apply(get_latest_price_from_changes)
        df['price_actual'] = df['price_from_changes'].fillna(df['price'])
        from_changes = df['price_from_changes'].notna().sum()
        from_offers = (df['price_actual'] == df['price']).sum()
        print(f"Актуальная цена: из price_changes={from_changes}, из offers.price={from_offers}")
    else:
        df['price_actual'] = df['price']
    return df


def filter_data(df):
    """Фильтрация данных"""
    initial_count = len(df)
    
    if 'category' in df.columns:
        before = len(df)
        df = df[df['category'] != 'dailyFlatRent'].copy()
        filtered_daily = before - len(df)
        if filtered_daily > 0:
            print(f"Отфильтровано dailyFlatRent: {filtered_daily} записей")
    
    if 'deal_type' in df.columns:
        before = len(df)
        df = df[df['deal_type'] == 'rent'].copy()
        filtered_sale = before - len(df)
        if filtered_sale > 0:
            print(f"Отфильтровано deal_type='sale': {filtered_sale} записей")
    
    print(f"После фильтрации: {len(df)} записей (было {initial_count})")
    return df


def clean_outliers(df):
    """Очистка выбросов"""
    initial_count = len(df)
    
    price_col = 'price_actual' if 'price_actual' in df.columns else 'price'
    df[price_col] = pd.to_numeric(df[price_col], errors='coerce')
    
    df = df[
        (df[price_col] >= 1000) & 
        (df[price_col] <= 10_000_000)
    ].copy()
    
    if 'total_area' in df.columns:
        df['total_area'] = pd.to_numeric(df['total_area'], errors='coerce')
        df = df[
            (df['total_area'] >= 10) & 
            (df['total_area'] <= 500)
        ].copy()
    
    filtered = initial_count - len(df)
    if filtered > 0:
        print(f"Отфильтровано выбросов: {filtered} записей")
    print(f"После очистки выбросов: {len(df)} записей")
    return df


def feature_engineering(df):
    """Feature Engineering"""
    print("\nFeature Engineering...")
    
    price_col = 'price_actual' if 'price_actual' in df.columns else 'price'
    
    if 'total_area' in df.columns and price_col in df.columns:
        df['total_area'] = pd.to_numeric(df['total_area'], errors='coerce')
        df['price_per_sqm'] = df[price_col] / df['total_area']
        print(f"Добавлено: price_per_sqm")
    
    if 'build_year' in df.columns:
        df['build_year'] = pd.to_numeric(df['build_year'], errors='coerce')
        df['house_age'] = 2025 - df['build_year']
        df['house_age'] = df['house_age'].clip(lower=0, upper=300)
        print(f"Добавлено: house_age")
    
    df = add_geo_features_v0(df)
    if 'distance_from_center' in df.columns:
        print(f"Добавлено: distance_from_center, distance_to_metro")
    
    return df


def fill_missing_values(df):
    """Заполнение пропусков"""
    print("\nЗаполнение пропусков...")
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    fill_dict = {}
    for col in numeric_cols:
        if df[col].isna().sum() > 0:
            fill_dict[col] = df[col].median()
    
    if fill_dict:
        df = df.fillna(fill_dict)
    
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        if col not in ['description', 'coordinates'] and df[col].isna().sum() > 0:
            df[col] = df[col].fillna('unknown')
    
    print("Пропуски заполнены")
    return df


def time_split(df, test_days=30):
    """Временное разделение на train/test"""
    df['publication_date'] = pd.to_datetime(df['publication_at'], unit='s', errors='coerce')
    df_with_date = df.dropna(subset=['publication_date']).copy()
    
    if len(df_with_date) == 0:
        raise ValueError("Нет записей с датой публикации")
    
    split_date = df_with_date['publication_date'].max() - timedelta(days=test_days)
    
    train_mask = df_with_date['publication_date'] <= split_date
    test_mask = df_with_date['publication_date'] > split_date
    
    train_df = df_with_date[train_mask].copy()
    test_df = df_with_date[test_mask].copy()
    
    print(f"\nВременное разделение (split_date={split_date.date()}):")
    print(f"Train: {len(train_df)} записей ({len(train_df)/len(df_with_date)*100:.1f}%)")
    print(f"Test: {len(test_df)} записей ({len(test_df)/len(df_with_date)*100:.1f}%)")
    
    return train_df, test_df


def prepare_data(output_dir=None):
    """Основная функция подготовки данных"""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / 'data' / 'processed'
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    env_path = Path(__file__).parent.parent / '.env'
    env = dotenv_values(env_path)
    
    DBTYPE = env.get('DB_TYPE') or 'mysql+pymysql'
    LOGIN = env.get('DB_LOGIN') or 'root'
    PASS = env.get('DB_PASS') or 'rootpassword'
    IP = env.get('DB_IP') or '89.110.92.128'
    PORT = env.get('DB_PORT') or '3306'
    DBNAME = env.get('DB_NAME') or 'rentsense'
    
    DATABASE_URL = f'{DBTYPE}://{LOGIN}:{PASS}@{IP}:{PORT}/{DBNAME}?charset=utf8mb4'
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    
    df = load_data_from_db(engine)
    df = add_price_actual(df)
    df = filter_data(df)
    df = clean_outliers(df)
    df = feature_engineering(df)
    df = fill_missing_values(df)
    
    train_df, test_df = time_split(df, test_days=30)
    
    train_path = output_dir / 'train.csv'
    test_path = output_dir / 'test.csv'
    
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    print(f"\nДанные сохранены:")
    print(f"Train: {train_path} ({len(train_df)} записей)")
    print(f"Test: {test_path} ({len(test_df)} записей)")
    
    return train_df, test_df


if __name__ == "__main__":
    train_df, test_df = prepare_data()
    print("\nПодготовка данных завершена!")

