"""
Кластеризация районов (KMeans, опционально HDBSCAN) для фичей модели.
"""
import logging
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# HDBSCAN опционален
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False


def add_cluster_features(df, n_clusters=5, use_hdbscan=True):
    """
    Добавление кластерных фичей в датафрейм.
    
    Создает фичи:
    - district_cluster_kmeans: кластер KMeans
    - district_cluster_hdbscan: кластер HDBSCAN (если доступен)
    - cluster_price_mean: средняя цена в кластере
    """
    df = df.copy()
    
    # Подготовка признаков для кластеризации
    cluster_features = []
    feature_names = []
    
    if 'distance_from_center' in df.columns:
        cluster_features.append('distance_from_center')
        feature_names.append('distance_from_center')
    
    if 'price_per_sqm' in df.columns:
        cluster_features.append('price_per_sqm')
        feature_names.append('price_per_sqm')
    
    if 'build_year' in df.columns:
        cluster_features.append('build_year')
        feature_names.append('build_year')
    
    # Дополнительные признаки, если доступны
    if 'total_area' in df.columns:
        cluster_features.append('total_area')
        feature_names.append('total_area')
    
    if len(cluster_features) < 2:
        # Если недостаточно признаков, возвращаем датафрейм без изменений
        return df
    
    # Создаем матрицу признаков для кластеризации
    X = df[cluster_features].copy()
    
    # Заполняем пропуски медианой
    for col in cluster_features:
        X[col] = pd.to_numeric(X[col], errors='coerce')
        median_val = X[col].median()
        if pd.notna(median_val):
            X[col] = X[col].fillna(median_val)
        else:
            X[col] = X[col].fillna(0)
    
    # Стандартизация признаков
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # KMeans кластеризация
    try:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df['district_cluster_kmeans'] = kmeans.fit_predict(X_scaled)
        
        # Средняя цена в каждом кластере
        if 'price_actual' in df.columns:
            price_col = 'price_actual'
        elif 'price' in df.columns:
            price_col = 'price'
        else:
            price_col = None
        
        if price_col:
            cluster_prices = df.groupby('district_cluster_kmeans')[price_col].mean().to_dict()
            df['cluster_price_mean'] = df['district_cluster_kmeans'].map(cluster_prices)
    except Exception as e:
        logger.warning("Ошибка KMeans: %s", e)
        df['district_cluster_kmeans'] = 0
        df['cluster_price_mean'] = df.get('price_actual', df.get('price', 0)).mean() if 'price_actual' in df.columns or 'price' in df.columns else 0
    
    # HDBSCAN кластеризация (если доступен)
    if use_hdbscan and HDBSCAN_AVAILABLE:
        try:
            hdbscan_clusterer = hdbscan.HDBSCAN(min_cluster_size=max(10, len(df) // 100), min_samples=5)
            df['district_cluster_hdbscan'] = hdbscan_clusterer.fit_predict(X_scaled)
            
            # -1 означает шум/выбросы в HDBSCAN
            # Заменяем на отдельную категорию
            df['district_cluster_hdbscan'] = df['district_cluster_hdbscan'].apply(
                lambda x: 'outlier' if x == -1 else f'cluster_{x}'
            )
        except Exception as e:
            logger.warning("Ошибка HDBSCAN: %s", e)
            df['district_cluster_hdbscan'] = 'cluster_0'
    else:
        if not HDBSCAN_AVAILABLE:
            logger.debug("HDBSCAN недоступен (pip install hdbscan)")
        df['district_cluster_hdbscan'] = 'cluster_0'
    
    return df


def add_cluster_features_simple(df, n_clusters=5):
    """
    Упрощенная версия кластеризации без HDBSCAN.
    Используется, если HDBSCAN недоступен.
    """
    return add_cluster_features(df, n_clusters=n_clusters, use_hdbscan=False)
