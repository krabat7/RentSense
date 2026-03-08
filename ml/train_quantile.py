"""
Скрипт обучения квантильных моделей для предсказания цены аренды.

Обучение CatBoost моделей с loss_function='Quantile' для квантилей [0.1, 0.5, 0.9],
что позволяет получить вилку цен (P10, P50, P90).
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
from prepare_data import prepare_data

from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


def calculate_mape(y_true, y_pred):
    """Вычисление MAPE (Mean Absolute Percentage Error)."""
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def calculate_quantile_metrics(y_true, y_pred_p10, y_pred_p50, y_pred_p90):
    """Вычисление метрик для квантильных предсказаний."""
    metrics = {}
    
    # Метрики для медианы (P50)
    metrics['P50_MAE'] = mean_absolute_error(y_true, y_pred_p50)
    metrics['P50_RMSE'] = np.sqrt(mean_squared_error(y_true, y_pred_p50))
    metrics['P50_MAPE'] = calculate_mape(y_true, y_pred_p50)
    
    # Покрытие вилки (сколько реальных значений попадает в интервал P10-P90)
    coverage = np.mean((y_true >= y_pred_p10) & (y_true <= y_pred_p90))
    metrics['coverage_p10_p90'] = coverage
    
    # Средняя ширина вилки
    width = np.mean(y_pred_p90 - y_pred_p10)
    metrics['mean_interval_width'] = width
    metrics['mean_interval_width_pct'] = (width / np.mean(y_true)) * 100 if np.mean(y_true) > 0 else 0
    
    # Квантильные ошибки
    errors_p10 = np.abs(y_true - y_pred_p10)
    errors_p50 = np.abs(y_true - y_pred_p50)
    errors_p90 = np.abs(y_true - y_pred_p90)
    
    metrics['P10_MAE'] = np.mean(errors_p10)
    metrics['P90_MAE'] = np.mean(errors_p90)
    
    return metrics


def prepare_features_for_quantile(df):
    """Подготовка признаков (используем ту же логику, что и в train_baseline)."""
    from train_baseline import prepare_features
    return prepare_features(df, use_correlation_filter=True, min_correlation=0.01)


def train_quantile_model(X_train, y_train, X_test, y_test, categorical_cols, 
                         quantile=0.5, run_name="catboost_quantile"):
    """Обучение CatBoost модели для конкретного квантиля."""
    print(f"\nОбучение CatBoost для квантиля {quantile}...")
    
    model = CatBoostRegressor(
        iterations=500,
        learning_rate=0.1,
        depth=6,
        loss_function='Quantile',
        loss_function_params={'alpha': quantile},
        eval_metric='Quantile:alpha={}'.format(quantile),
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
        'MAE': mean_absolute_error(y_train, y_pred_train),
        'RMSE': np.sqrt(mean_squared_error(y_train, y_pred_train)),
        'MAPE': calculate_mape(y_train, y_pred_train)
    }
    
    metrics_test = {
        'MAE': mean_absolute_error(y_test, y_pred_test),
        'RMSE': np.sqrt(mean_squared_error(y_test, y_pred_test)),
        'MAPE': calculate_mape(y_test, y_pred_test)
    }
    
    print(f"\nМетрики (Train): MAE={metrics_train['MAE']:.2f}, RMSE={metrics_train['RMSE']:.2f}, MAPE={metrics_train['MAPE']:.2f}%")
    print(f"Метрики (Test): MAE={metrics_test['MAE']:.2f}, RMSE={metrics_test['RMSE']:.2f}, MAPE={metrics_test['MAPE']:.2f}%")
    
    return model, metrics_train, metrics_test, y_pred_test


def main():
    """Основная функция обучения квантильных моделей."""
    print("=" * 60)
    print("Обучение квантильных моделей")
    print("=" * 60)
    
    # Инициализация MLflow
    init_mlflow()
    
    # Загрузка и подготовка данных
    print("\nЗагрузка данных...")
    train_df, test_df = prepare_data()
    
    print(f"Train: {len(train_df)} записей")
    print(f"Test: {len(test_df)} записей")
    
    # Подготовка признаков
    X_train, y_train, categorical_cols, numeric_cols, feature_cols = prepare_features_for_quantile(train_df)
    X_test, y_test, _, _, _ = prepare_features_for_quantile(test_df)
    
    # Обучение моделей для трех квантилей
    quantiles = [0.1, 0.5, 0.9]  # P10, P50, P90
    models = {}
    predictions = {}
    all_metrics = {}
    
    with mlflow.start_run(run_name="quantile_regression_v2"):
        mlflow.set_tag("model_version", "v2")
        mlflow.set_tag("model_type", "quantile")
        
        for quantile in quantiles:
            quantile_name = f"P{int(quantile * 100)}"
            run_name = f"catboost_quantile_{quantile_name}"
            
            model, metrics_train, metrics_test, y_pred_test = train_quantile_model(
                X_train, y_train, X_test, y_test,
                categorical_cols, quantile=quantile, run_name=run_name
            )
            
            models[quantile_name] = model
            predictions[quantile_name] = y_pred_test
            all_metrics[quantile_name] = {
                'train': metrics_train,
                'test': metrics_test
            }
            
            # Логирование в MLflow
            mlflow.log_metrics({
                f"{quantile_name}_train_MAE": metrics_train['MAE'],
                f"{quantile_name}_train_RMSE": metrics_train['RMSE'],
                f"{quantile_name}_train_MAPE": metrics_train['MAPE'],
                f"{quantile_name}_test_MAE": metrics_test['MAE'],
                f"{quantile_name}_test_RMSE": metrics_test['RMSE'],
                f"{quantile_name}_test_MAPE": metrics_test['MAPE'],
            })
            
            # Сохранение модели
            model_path = f"ml/models/catboost_quantile_{quantile_name}_v2.model"
            model.save_model(model_path)
            mlflow.log_artifact(model_path, "models")
            print(f"Модель сохранена: {model_path}")
        
        # Вычисление метрик для вилки
        quantile_metrics = calculate_quantile_metrics(
            y_test.values,
            predictions['P10'],
            predictions['P50'],
            predictions['P90']
        )
        
        mlflow.log_metrics(quantile_metrics)
        
        print("\n" + "=" * 60)
        print("Метрики вилки цен (P10-P90):")
        print("=" * 60)
        for key, value in quantile_metrics.items():
            print(f"  {key}: {value:.2f}")
        
        # Логирование параметров
        mlflow.log_params({
            'quantiles': str(quantiles),
            'n_features': len(feature_cols),
            'n_categorical': len(categorical_cols),
            'n_numeric': len(numeric_cols),
        })
        
        print("\nМодели обучены и залогированы в MLflow")
        print("=" * 60)


if __name__ == "__main__":
    main()
