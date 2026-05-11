"""Smoke-тесты FastAPI: health и predict с моком baseline-модели."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _minimal_predict_body():
    cid = 12_345
    return {
        "id": "test-1",
        "data": {
            "cian_id": cid,
            "price": 60_000.0,
            "category": "flatRent",
            "views_count": 10,
            "photos_count": 5,
            "floor_number": 3,
            "floors_count": 9,
            "publication_at": 1_700_000_000,
            "county": "Москва",
            "district": "Тверской",
            "street": "Тверская",
            "house": "1",
            "metro": "Тверская",
            "travel_type": "walk",
            "travel_time": 10,
            "coordinates": {"lat": 55.7536, "lng": 37.621},
            "repair_type": "cosmetic",
            "total_area": 40.0,
            "living_area": 20.0,
            "kitchen_area": 8.0,
            "ceiling_height": 2.7,
            "balconies": 1,
            "loggias": 0,
            "rooms_count": 2,
            "separated_wc": 0.0,
            "combined_wc": 1,
            "windows_view": "street",
            "build_year": 2010,
            "entrances": 1,
            "material_type": "panel",
            "parking_type": None,
            "garbage_chute": False,
            "lifts_count": 2,
            "passenger_lifts": 2,
            "cargo_lifts": 0,
            "realty_type": "flat",
            "project_type": "Индивидуальный проект",
            "heat_type": None,
            "gas_type": None,
            "is_apartment": False,
            "is_penthouse": False,
            "is_mortgage_allowed": False,
            "is_premium": False,
            "is_emergency": False,
            "renovation_programm": False,
            "finish_date": None,
            "agent_name": None,
            "deal_type": "rent",
            "flat_type": "rooms",
            "sale_type": None,
            "description": None,
            "name": None,
            "review_count": None,
            "total_rate": None,
            "buildings_count": None,
            "foundation_year": None,
            "is_reliable": None,
        },
        "sysmodel": "catboost",
    }


@pytest.fixture
def api_app():
    from app.api import main as api_main

    return api_main.app


def test_health_ok(api_app):
    client = TestClient(api_app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_predict_baseline_with_mock_model(api_app, monkeypatch):
    from app.api import main as api_main
    from app.api import model_loader as ml_mod

    mock = MagicMock()
    mock.feature_names_ = None
    mock.predict = MagicMock(return_value=np.array([75_000.0], dtype=np.float64))

    monkeypatch.setattr(api_main, "quantile_models", {})
    monkeypatch.setattr(api_main, "baseline_model", mock)
    monkeypatch.setattr(ml_mod, "BASELINE_LOG_TARGET", False)

    client = TestClient(api_app)
    r = client.post("/api/predict", json=_minimal_predict_body())
    assert r.status_code == 200
    body = r.json()
    assert body["price"] == 75_000.0
    mock.predict.assert_called_once()


def test_rate_limit_predict_returns_429_when_exceeded(api_app, monkeypatch):
    from app.api import main as api_main
    from app.api import model_loader as ml_mod
    from app.api.rate_limit import clear_rate_limit_state

    mock = MagicMock()
    mock.feature_names_ = None
    mock.predict = MagicMock(return_value=np.array([75_000.0], dtype=np.float64))
    monkeypatch.setattr(api_main, "quantile_models", {})
    monkeypatch.setattr(api_main, "baseline_model", mock)
    monkeypatch.setattr(ml_mod, "BASELINE_LOG_TARGET", False)

    monkeypatch.setenv("RS_RATE_LIMIT_ENABLED", "1")
    monkeypatch.setenv("RS_RATE_LIMIT_API_PER_MINUTE", "2")
    clear_rate_limit_state()

    client = TestClient(api_app)
    body = _minimal_predict_body()
    assert client.post("/api/predict", json=body).status_code == 200
    assert client.post("/api/predict", json=body).status_code == 200
    r = client.post("/api/predict", json=body)
    assert r.status_code == 429
    mock.predict.assert_called()
