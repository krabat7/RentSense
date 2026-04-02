"""Фичи v2 для модели предсказания цены аренды."""

from .geo_features import add_geo_features_v0, calculate_distance_from_center
from .travel_features import add_travel_features
from .seasonal_features import add_seasonal_features, add_seasonal_aggregates
from .building_features import add_building_features
from .interaction_features import add_interaction_features
from .cluster_features import add_cluster_features, add_cluster_features_simple


def add_features_v2(df, use_clustering=True, n_clusters=5):
    """Цепочка: гео, метро/время, сезонность, дом; опционально кластеры районов."""
    df = add_geo_features_v0(df)
    df = add_travel_features(df)
    df = add_seasonal_features(df)
    df = add_building_features(df)
    # Интеракции в prepare_data / inference после price_per_sqm.
    if use_clustering:
        try:
            df = add_cluster_features(df, n_clusters=n_clusters)
        except Exception:
            df = add_cluster_features_simple(df, n_clusters=n_clusters)
    return df
