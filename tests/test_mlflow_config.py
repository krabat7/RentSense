"""Тесты для конфигурации MLflow."""
import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from ml.mlflow_config import EXPERIMENT_NAME, MLFLOW_TRACKING_URI


def test_mlflow_config():
    """Тест конфигурации MLflow."""
    assert EXPERIMENT_NAME == "rentsense-rent-prediction"
    assert MLFLOW_TRACKING_URI is not None
    assert isinstance(MLFLOW_TRACKING_URI, str)

