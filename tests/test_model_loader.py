"""Тесты загрузчика моделей (app/api/model_loader.py)."""
import sys
from pathlib import Path

import numpy as np
import pytest
from catboost import CatBoostRegressor

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api import model_loader


@pytest.fixture(autouse=True)
def _clear_model_cache():
    model_loader.clear_cache()
    yield
    model_loader.clear_cache()


def _save_minimal_catboost(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    X = np.array([[1.0], [2.0], [3.0]], dtype=np.float64)
    y = np.array([10.0, 20.0, 30.0], dtype=np.float64)
    m = CatBoostRegressor(iterations=2, depth=2, loss_function="RMSE", verbose=False)
    m.fit(X, y)
    m.save_model(str(path))


def test_load_model_file_missing():
    missing = ROOT / "ml" / "models" / "___no_such_model___.cbm"
    with pytest.raises(FileNotFoundError, match="Модель не найдена"):
        model_loader.load_model(str(missing), "catboost")


def test_load_model_unsupported_type(tmp_path):
    p = tmp_path / "m.cbm"
    _save_minimal_catboost(p)
    with pytest.raises(ValueError, match="Неподдерживаемый тип"):
        model_loader.load_model(str(p), "xgboost")


def test_load_model_roundtrip(tmp_path):
    p = tmp_path / "tiny.cbm"
    _save_minimal_catboost(p)
    m = model_loader.load_model(str(p), "catboost")
    pred = m.predict(np.array([[2.0]], dtype=np.float64))
    assert pred.shape == (1,)
    assert np.isfinite(pred[0])


def test_load_baseline_model_missing(tmp_path):
    empty_dir = tmp_path / "empty_models"
    empty_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="Baseline модель не найдена"):
        model_loader.load_baseline_model("catboost", models_dir=str(empty_dir))


def test_load_baseline_model_success(tmp_path):
    d = tmp_path / "models"
    d.mkdir()
    p = d / "catboost_baseline.model"
    _save_minimal_catboost(p)
    m = model_loader.load_baseline_model("catboost", models_dir=str(d))
    out = m.predict(np.array([[2.0]], dtype=np.float64))
    assert np.isfinite(out[0])


def test_get_cached_model_returns_same_instance(tmp_path):
    p = tmp_path / "cached.cbm"
    _save_minimal_catboost(p)
    a = model_loader.get_cached_model("k1", str(p), "catboost")
    b = model_loader.get_cached_model("k1", str(p), "catboost")
    assert a is b
