"""
Скрипт обучения бейзлайн моделей для предсказания цены аренды.

Обучение CatBoost и LightGBM моделей регрессии с метриками MAE, RMSE, MAPE,
квантилями P10, P50, P90 и логированием в MLflow.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
import mlflow
from mlflow.models import infer_signature

sys.path.append(str(Path(__file__).parent))
from mlflow_config import init_mlflow

from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


def calculate_mape(y_true, y_pred):
    """Вычисление MAPE (Mean Absolute Percentage Error)."""
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def calculate_quantiles(y_true, y_pred):
    """Вычисление квантилей ошибки: P10, P50, P90."""
    errors = np.abs(y_true - y_pred)
    return {
        'P10': np.percentile(errors, 10),
        'P50': np.percentile(errors, 50),
        'P90': np.percentile(errors, 90)
    }


def prepare_features(df):
    """Подготовка признаков для обучения."""
    target_col = 'price_actual' if 'price_actual' in df.columns else 'price'
    
    exclude_cols = [
        'cian_id', 'price', 'price_changes', 'price_from_changes', 
        'price_actual', 'publication_at', 'publication_date',
        'offer_created_at', 'offer_updated_at',
        'description', 'coordinates'
    ]
    
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    X = df[feature_cols].copy()
    y = df[target_col].copy()
    
    y = pd.to_numeric(y, errors='coerce')
    
    categorical_cols_base = [
        'category', 'county', 'district', 'street', 'house', 'metro',
        'travel_type', 'repair_type', 'windows_view', 'material_type',
        'parking_type', 'realty_type', 'project_type', 'heat_type',
        'gas_type', 'deal_type', 'flat_type', 'payment_period',
        'developer_name', 'district_encoded'
    ]
    
    categorical_cols = []
    numeric_cols = []
    
    for col in X.columns:
        if col in categorical_cols_base or X[col].dtype == 'object':
            X[col] = X[col].astype(str).fillna('unknown')
            categorical_cols.append(col)
        else:
            X[col] = pd.to_numeric(X[col], errors='coerce')
            if X[col].isna().any():
                X[col] = X[col].fillna(0)
            numeric_cols.append(col)
    
    print(f"Признаков: {len(feature_cols)}")
    print(f"  Числовых: {len(numeric_cols)}")
    print(f"  Категориальных: {len(categorical_cols)}")
    
    return X, y, categorical_cols, numeric_cols, feature_cols


def train_catboost(X_train, y_train, X_test, y_test, categorical_cols, run_name="catboost_baseline"):
    """Обучение CatBoost модели."""
    print("\nОбучение CatBoost...")
    
    model = CatBoostRegressor(
        iterations=500,
        learning_rate=0.1,
        depth=6,
        loss_function='RMSE',
        eval_metric='RMSE',
        random_seed=42,
        verbose=100,
        cat_features=categorical_cols if categorical_cols else None
    )
    
    model.fit(
        X_train, y_train,
        eval_set=(X_test, y_test),
        use_best_model=True,
        verbose=100
    )
    
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    metrics_train = {
        'train_mae': mean_absolute_error(y_train, y_pred_train),
        'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
        'train_mape': calculate_mape(y_train, y_pred_train)
    }
    
    metrics_test = {
        'test_mae': mean_absolute_error(y_test, y_pred_test),
        'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test)),
        'test_mape': calculate_mape(y_test, y_pred_test)
    }
    
    quantiles_test = calculate_quantiles(y_test, y_pred_test)
    
    print(f"\nМетрики CatBoost (Train):")
    print(f"  MAE: {metrics_train['train_mae']:.2f}")
    print(f"  RMSE: {metrics_train['train_rmse']:.2f}")
    print(f"  MAPE: {metrics_train['train_mape']:.2f}%")
    
    print(f"\nМетрики CatBoost (Test):")
    print(f"  MAE: {metrics_test['test_mae']:.2f}")
    print(f"  RMSE: {metrics_test['test_rmse']:.2f}")
    print(f"  MAPE: {metrics_test['test_mape']:.2f}%")
    
    print(f"\nКвантили ошибки (Test):")
    print(f"  P10: {quantiles_test['P10']:.2f}")
    print(f"  P50: {quantiles_test['P50']:.2f}")
    print(f"  P90: {quantiles_test['P90']:.2f}")
    
    return model, metrics_train, metrics_test, quantiles_test


def train_lightgbm(X_train, y_train, X_test, y_test, categorical_cols, run_name="lightgbm_baseline"):
    """Обучение LightGBM модели."""
    print("\nОбучение LightGBM...")
    
    X_train_lgb = X_train.copy()
    X_test_lgb = X_test.copy()
    
    for col in categorical_cols:
        if col in X_train_lgb.columns:
            X_train_lgb[col] = X_train_lgb[col].astype('category')
            X_test_lgb[col] = X_test_lgb[col].astype('category')
    
    for col in X_train_lgb.select_dtypes(include=['object']).columns:
        if col not in categorical_cols:
            X_train_lgb[col] = pd.to_numeric(X_train_lgb[col], errors='coerce').fillna(0)
            X_test_lgb[col] = pd.to_numeric(X_test_lgb[col], errors='coerce').fillna(0)
    
    model = LGBMRegressor(
        n_estimators=500,
        learning_rate=0.1,
        max_depth=6,
        random_state=42,
        verbose=-1
    )
    
    model.fit(
        X_train_lgb, y_train,
        eval_set=[(X_test_lgb, y_test)],
        eval_metric='rmse',
        callbacks=[lambda env: None]
    )
    
    y_pred_train = model.predict(X_train_lgb)
    y_pred_test = model.predict(X_test_lgb)
    
    metrics_train = {
        'train_mae': mean_absolute_error(y_train, y_pred_train),
        'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
        'train_mape': calculate_mape(y_train, y_pred_train)
    }
    
    metrics_test = {
        'test_mae': mean_absolute_error(y_test, y_pred_test),
        'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test)),
        'test_mape': calculate_mape(y_test, y_pred_test)
    }
    
    quantiles_test = calculate_quantiles(y_test, y_pred_test)
    
    print(f"\nМетрики LightGBM (Train):")
    print(f"  MAE: {metrics_train['train_mae']:.2f}")
    print(f"  RMSE: {metrics_train['train_rmse']:.2f}")
    print(f"  MAPE: {metrics_train['train_mape']:.2f}%")
    
    print(f"\nМетрики LightGBM (Test):")
    print(f"  MAE: {metrics_test['test_mae']:.2f}")
    print(f"  RMSE: {metrics_test['test_rmse']:.2f}")
    print(f"  MAPE: {metrics_test['test_mape']:.2f}%")
    
    print(f"\nКвантили ошибки (Test):")
    print(f"  P10: {quantiles_test['P10']:.2f}")
    print(f"  P50: {quantiles_test['P50']:.2f}")
    print(f"  P90: {quantiles_test['P90']:.2f}")
    
    model._X_train_prepared = X_train_lgb
    
    return model, metrics_train, metrics_test, quantiles_test


def log_model_to_mlflow(model, model_name, X_train, y_train, metrics_train, metrics_test, quantiles_test):
    """Логирование модели в MLflow."""
    with mlflow.start_run(run_name=f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        mlflow.log_param("model_name", model_name)
        mlflow.log_param("train_size", len(X_train))
        
        for key, value in metrics_train.items():
            mlflow.log_metric(key, value)
        
        for key, value in metrics_test.items():
            mlflow.log_metric(key, value)
        
        for key, value in quantiles_test.items():
            mlflow.log_metric(f"test_{key.lower()}", value)
        
        if model_name == "lightgbm" and hasattr(model, '_X_train_prepared'):
            X_for_signature = model._X_train_prepared
        else:
            X_for_signature = X_train
        
        signature = infer_signature(X_for_signature, model.predict(X_for_signature))
        
        if model_name == "catboost":
            mlflow.catboost.log_model(model, "model", signature=signature)
        elif model_name == "lightgbm":
            mlflow.lightgbm.log_model(model, "model", signature=signature)
        
        print(f"Модель {model_name} сохранена в MLflow")


def save_model(model, model_name, output_dir):
    """Сохранение модели в файл."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = output_dir / f"{model_name}_baseline.model"
    
    if model_name == "catboost":
        model.save_model(str(model_path))
    elif model_name == "lightgbm":
        model.booster_.save_model(str(model_path))
    
    print(f"Модель сохранена: {model_path}")
    return model_path


def train_baseline_models(data_dir=None, models_dir=None):
    """Основная функция обучения моделей."""
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / 'data' / 'processed'
    data_dir = Path(data_dir)
    
    if models_dir is None:
        models_dir = Path(__file__).parent / 'models'
    models_dir = Path(models_dir)
    
    print("Загрузка данных...")
    train_df = pd.read_csv(data_dir / 'train.csv')
    test_df = pd.read_csv(data_dir / 'test.csv')
    
    print(f"Train: {len(train_df)} записей")
    print(f"Test: {len(test_df)} записей")
    
    print("\nПодготовка признаков...")
    X_train, y_train, cat_cols_train, num_cols_train, feature_cols = prepare_features(train_df)
    X_test, y_test, _, _, _ = prepare_features(test_df)
    
    print(f"\nЦелевая переменная (Train):")
    print(f"  Медиана: {y_train.median():.2f}")
    print(f"  Среднее: {y_train.mean():.2f}")
    print(f"  Мин/Макс: {y_train.min():.2f} / {y_train.max():.2f}")
    
    init_mlflow()
    
    print("\n" + "="*60)
    cat_model, cat_metrics_train, cat_metrics_test, cat_quantiles = train_catboost(
        X_train, y_train, X_test, y_test, cat_cols_train, run_name="catboost_baseline"
    )
    log_model_to_mlflow(
        cat_model, "catboost", X_train, y_train,
        cat_metrics_train, cat_metrics_test, cat_quantiles
    )
    save_model(cat_model, "catboost", models_dir)
    
    print("\n" + "="*60)
    lgb_model, lgb_metrics_train, lgb_metrics_test, lgb_quantiles = train_lightgbm(
        X_train, y_train, X_test, y_test, cat_cols_train, run_name="lightgbm_baseline"
    )
    log_model_to_mlflow(
        lgb_model, "lightgbm", X_train, y_train,
        lgb_metrics_train, lgb_metrics_test, lgb_quantiles
    )
    save_model(lgb_model, "lightgbm", models_dir)
    
    print("\n" + "="*60)
    print("Обучение завершено!")
    print(f"Модели сохранены в: {models_dir}")
    
    return cat_model, lgb_model


if __name__ == "__main__":
    cat_model, lgb_model = train_baseline_models()

