"""
Дополнительные метрики для оценки моделей предсказания цены аренды.

R², Median Absolute Error, Symmetric MAPE, метрики по ценовым сегментам.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error


def calculate_r2(y_true, y_pred):
    """Вычисление R² (коэффициент детерминации)."""
    return r2_score(y_true, y_pred)


def calculate_median_ae(y_true, y_pred):
    """Вычисление Median Absolute Error."""
    errors = np.abs(y_true - y_pred)
    return np.median(errors)


def calculate_symmetric_mape(y_true, y_pred):
    """Вычисление Symmetric MAPE (sMAPE).
    
    sMAPE = mean(200 * |y_true - y_pred| / (|y_true| + |y_pred|))
    """
    numerator = np.abs(y_true - y_pred)
    denominator = np.abs(y_true) + np.abs(y_pred)
    mask = denominator != 0
    return np.mean(200 * numerator[mask] / denominator[mask])


def calculate_metrics_by_segments(y_true, y_pred, segments=None):
    """Вычисление метрик по ценовым сегментам.
    
    Args:
        y_true: Реальные значения
        y_pred: Предсказанные значения
        segments: Словарь с границами сегментов. По умолчанию:
            - cheap: < 50k
            - medium: 50k - 150k
            - expensive: > 150k
    
    Returns:
        Словарь с метриками для каждого сегмента
    """
    if segments is None:
        segments = {
            'cheap': (0, 50000),
            'medium': (50000, 150000),
            'expensive': (150000, np.inf)
        }
    
    results = {}
    
    for segment_name, (min_val, max_val) in segments.items():
        mask = (y_true >= min_val) & (y_true < max_val)
        
        if mask.sum() == 0:
            results[segment_name] = {
                'count': 0,
                'mae': None,
                'rmse': None,
                'mape': None,
                'r2': None
            }
            continue
        
        y_true_seg = y_true[mask]
        y_pred_seg = y_pred[mask]
        
        results[segment_name] = {
            'count': len(y_true_seg),
            'mae': mean_absolute_error(y_true_seg, y_pred_seg),
            'rmse': np.sqrt(mean_squared_error(y_true_seg, y_pred_seg)),
            'mape': calculate_mape(y_true_seg, y_pred_seg),
            'r2': r2_score(y_true_seg, y_pred_seg)
        }
    
    return results


def calculate_mape(y_true, y_pred):
    """Вычисление MAPE (Mean Absolute Percentage Error)."""
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def calculate_all_metrics(y_true, y_pred, segments=None):
    """Вычисление всех метрик.
    
    Returns:
        Словарь со всеми метриками
    """
    metrics = {
        'MAE': mean_absolute_error(y_true, y_pred),
        'RMSE': np.sqrt(mean_squared_error(y_true, y_pred)),
        'MAPE': calculate_mape(y_true, y_pred),
        'R2': calculate_r2(y_true, y_pred),
        'Median_AE': calculate_median_ae(y_true, y_pred),
        'Symmetric_MAPE': calculate_symmetric_mape(y_true, y_pred)
    }
    
    if segments is not None:
        metrics['by_segments'] = calculate_metrics_by_segments(y_true, y_pred, segments)
    
    return metrics


def print_metrics(metrics, title="Метрики"):
    """Печать метрик в читаемом формате."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    print("\nОбщие метрики:")
    print(f"  MAE: {metrics['MAE']:.2f}")
    print(f"  RMSE: {metrics['RMSE']:.2f}")
    print(f"  MAPE: {metrics['MAPE']:.2f}%")
    print(f"  R²: {metrics['R2']:.4f}")
    print(f"  Median AE: {metrics['Median_AE']:.2f}")
    print(f"  Symmetric MAPE: {metrics['Symmetric_MAPE']:.2f}%")
    
    if 'by_segments' in metrics:
        print("\nМетрики по сегментам:")
        for segment_name, seg_metrics in metrics['by_segments'].items():
            if seg_metrics['count'] > 0:
                print(f"\n  {segment_name.upper()} (n={seg_metrics['count']}):")
                print(f"    MAE: {seg_metrics['mae']:.2f}")
                print(f"    RMSE: {seg_metrics['rmse']:.2f}")
                print(f"    MAPE: {seg_metrics['mape']:.2f}%")
                print(f"    R²: {seg_metrics['r2']:.4f}")
    
    print(f"{'='*60}\n")
