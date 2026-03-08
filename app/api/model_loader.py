"""Загрузка и кэш CatBoost-моделей (baseline и квантильные) для inference."""
from pathlib import Path
import logging
from typing import Optional, Dict, Any
from catboost import CatBoostRegressor

logger = logging.getLogger(__name__)

# Глобальный кэш моделей
_models_cache: Dict[str, Any] = {}


def load_model(model_path: str, model_type: str = 'catboost') -> CatBoostRegressor:
    """Загрузка модели из файла (catboost/lightgbm)."""
    model_path = Path(model_path)
    
    if not model_path.exists():
        raise FileNotFoundError(f"Модель не найдена: {model_path}")
    
    if model_type == 'catboost':
        model = CatBoostRegressor()
        model.load_model(str(model_path))
        logger.info(f"Модель загружена: {model_path}")
        return model
    else:
        raise ValueError(f"Неподдерживаемый тип модели: {model_type}")


def get_cached_model(model_key: str, model_path: str, model_type: str = 'catboost') -> CatBoostRegressor:
    """Модель из кэша или загрузка по пути."""
    if model_key not in _models_cache:
        _models_cache[model_key] = load_model(model_path, model_type)
        logger.info(f"Модель добавлена в кэш: {model_key}")
    else:
        logger.debug(f"Модель взята из кэша: {model_key}")
    
    return _models_cache[model_key]


def load_quantile_models(models_dir: Optional[str] = None) -> Dict[str, CatBoostRegressor]:
    """Загрузка квантильных моделей P10, P50, P90 из ml/models/ или указанной директории."""
    if models_dir is None:
        models_dir = Path(__file__).parent.parent.parent / 'ml' / 'models'
    else:
        models_dir = Path(models_dir)
    
    quantiles = ['P10', 'P50', 'P90']
    models = {}
    
    for quantile in quantiles:
        model_path = models_dir / f"catboost_quantile_{quantile}_v2.model"
        
        if model_path.exists():
            model_key = f"quantile_{quantile}"
            models[quantile] = get_cached_model(model_key, str(model_path), 'catboost')
        else:
            logger.warning(f"Модель для квантиля {quantile} не найдена: {model_path}")
    
    return models


def load_baseline_model(model_name: str = 'catboost', models_dir: Optional[str] = None) -> CatBoostRegressor:
    """Загрузка baseline-модели (catboost/lightgbm)."""
    if models_dir is None:
        models_dir = Path(__file__).parent.parent.parent / 'ml' / 'models'
    else:
        models_dir = Path(models_dir)
    
    model_path = models_dir / f"{model_name}_baseline.model"
    
    if not model_path.exists():
        raise FileNotFoundError(f"Baseline модель не найдена: {model_path}")
    
    model_key = f"baseline_{model_name}"
    return get_cached_model(model_key, str(model_path), 'catboost' if model_name == 'catboost' else 'lightgbm')


def clear_cache():
    """Очистка кэша моделей."""
    global _models_cache
    _models_cache.clear()
    logger.info("Кэш моделей очищен")
