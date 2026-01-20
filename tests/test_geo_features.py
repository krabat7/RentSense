"""Тесты для гео-фичей."""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from ml.features.geo_features import calculate_distance_from_center, add_geo_features_v0


def test_calculate_distance_from_center():
    """Тест расчета расстояния от центра Москвы."""
    lat, lng = 55.753600, 37.621184
    distance = calculate_distance_from_center(lat, lng)
    assert distance == 0.0
    assert isinstance(distance, float)
    
    lat2, lng2 = 55.76, 37.63
    distance2 = calculate_distance_from_center(lat2, lng2)
    assert distance2 > 0
    assert isinstance(distance2, float)


def test_add_geo_features_v0():
    """Тест добавления гео-фичей."""
    df = pd.DataFrame({
        'coordinates': [
            {'lat': 55.753600, 'lng': 37.621184},
            {'lat': 55.76, 'lng': 37.63},
            None
        ],
        'travel_time': [10, 15, None],
        'district': ['Центральный', 'Тверской', None]
    })
    
    result = add_geo_features_v0(df)
    
    assert 'lat' in result.columns
    assert 'lng' in result.columns
    assert 'distance_from_center' in result.columns
    assert 'distance_to_metro' in result.columns
    assert 'district_encoded' in result.columns
    
    assert result['distance_from_center'].iloc[0] == 0.0
    assert pd.notna(result['distance_from_center'].iloc[1])
    assert pd.isna(result['distance_from_center'].iloc[2])

