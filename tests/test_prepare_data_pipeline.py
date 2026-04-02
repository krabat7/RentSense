"""Тесты фильтрации, дедупликации и очистки выбросов (ml/prepare_data.py)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.prepare_data import filter_data, remove_duplicates, clean_outliers


def _base_row(**overrides):
    row = {
        "cian_id": 1,
        "category": "flatRent",
        "deal_type": "rent",
        "price_actual": 50_000.0,
        "price": 50_000.0,
        "floor_number": 5,
        "total_area": 40.0,
        "rooms_count": 1,
        "street": "Тверская",
        "house": "1",
        "publication_at": 1_700_000_000,
    }
    row.update(overrides)
    return row


def test_filter_data_removes_daily_flat_and_sale():
    df = pd.DataFrame(
        [
            _base_row(),
            _base_row(category="dailyFlatRent", cian_id=2),
            _base_row(deal_type="sale", cian_id=3),
        ]
    )
    out = filter_data(df)
    assert len(out) == 1
    assert out.iloc[0]["category"] == "flatRent"
    assert out.iloc[0]["deal_type"] == "rent"


def test_filter_data_without_optional_columns():
    df = pd.DataFrame([{"price": 1000}])
    out = filter_data(df)
    assert len(out) == 1


def test_remove_duplicates_keeps_newer_publication():
    newer_ts = 1_800_000_000
    older_ts = 1_700_000_000
    df = pd.DataFrame(
        [
            _base_row(cian_id=1, publication_at=older_ts, price_actual=40_000),
            _base_row(cian_id=2, publication_at=newer_ts, price_actual=55_000),
        ]
    )
    out = remove_duplicates(df)
    assert len(out) == 1
    assert int(out.iloc[0]["publication_at"]) == newer_ts
    assert int(out.iloc[0]["cian_id"]) == 2


def test_remove_duplicates_street_house_normalized():
    df = pd.DataFrame(
        [
            _base_row(cian_id=1, street="  Тверская ", house="1", publication_at=1_800_000_000),
            _base_row(cian_id=2, street="тверская", house="1", publication_at=1_700_000_000),
        ]
    )
    out = remove_duplicates(df)
    assert len(out) == 1


def test_clean_outliers_price_bounds():
    df = pd.DataFrame(
        [
            _base_row(price_actual=500, total_area=40),
            _base_row(price_actual=50_000, total_area=40, cian_id=2),
            _base_row(price_actual=20_000_000, total_area=40, cian_id=3),
        ]
    )
    out = clean_outliers(df)
    assert len(out) == 1
    assert out.iloc[0]["price_actual"] == 50_000


def test_clean_outliers_area_and_price_per_sqm():
    # Строка 1: площадь <10; строка 2: price/m2 > 100k; строка 3: валидная.
    df = pd.DataFrame(
        [
            _base_row(price_actual=50_000, total_area=5, cian_id=1),
            _base_row(price_actual=9_000_000, total_area=40, cian_id=2),
            _base_row(price_actual=50_000, total_area=40, cian_id=3),
        ]
    )
    out = clean_outliers(df)
    assert set(out["cian_id"].tolist()) == {3}


def test_clean_outliers_total_area_zero_no_crash():
    df = pd.DataFrame(
        [
            _base_row(price_actual=50_000, total_area=0, cian_id=1),
            _base_row(price_actual=50_000, total_area=40, cian_id=2),
        ]
    )
    out = clean_outliers(df)
    assert len(out) == 1
    assert int(out.iloc[0]["cian_id"]) == 2


def test_clean_outliers_uses_price_when_no_price_actual():
    df = pd.DataFrame(
        [
            {"price": 50_000, "total_area": 40},
            {"price": 500, "total_area": 40},
        ]
    )
    out = clean_outliers(df)
    assert len(out) == 1
    assert out.iloc[0]["price"] == 50_000
