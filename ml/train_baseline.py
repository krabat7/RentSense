"""
Скрипт обучения бейзлайн моделей для предсказания цены аренды.

Обучение CatBoost, LightGBM и XGBoost моделей регрессии с метриками MAE, RMSE, MAPE,
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
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import OrdinalEncoder


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


def _prepare_x_for_lgb_xgb(X, categorical_cols):
    """Копия матрицы признаков в том же виде, что при обучении LGBM/XGB."""
    Xp = X.copy()
    for col in categorical_cols:
        if col in Xp.columns:
            Xp[col] = Xp[col].astype('category')
    for col in Xp.select_dtypes(include=['object']).columns:
        if col not in categorical_cols:
            Xp[col] = pd.to_numeric(Xp[col], errors='coerce').fillna(0)
    return Xp


def _prepare_x_for_xgb_inference(X, xgb_model):
    """Та же обработка категорий, что в train_xgboost (OrdinalEncoder с модели)."""
    Xp = X.copy()
    enc = getattr(xgb_model, "_xgb_ord_enc", None)
    cats = getattr(xgb_model, "_xgb_cat_present", None) or []
    if enc is not None and cats:
        Xp[cats] = enc.transform(Xp[cats].astype(str))
    for col in Xp.select_dtypes(include=["object"]).columns:
        Xp[col] = pd.to_numeric(Xp[col], errors="coerce").fillna(0)
    return Xp.astype(np.float64)


def analyze_correlations(df, target_col='price_actual', min_corr=0.01):
    """Анализ корреляций с целевой переменной"""
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if target_col not in numeric_cols:
        return []
    
    correlations = {}
    for col in numeric_cols:
        if col != target_col:
            try:
                corr = df[[col, target_col]].corr().iloc[0, 1]
                if not np.isnan(corr):
                    correlations[col] = abs(corr)
            except:
                pass
    
    sorted_corr = sorted(correlations.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\nКорреляции с {target_col} (топ-20):")
    for col, corr in sorted_corr[:20]:
        print(f"  {col}: {corr:.4f}")
    
    low_corr_cols = [col for col, corr in correlations.items() if abs(corr) < min_corr]
    
    if low_corr_cols:
        print(f"\nПризнаки с низкой корреляцией (<{min_corr}): {len(low_corr_cols)}")
        print(f"  Примеры: {low_corr_cols[:10]}")
    
    return sorted_corr


def prepare_features(
    df,
    use_correlation_filter=True,
    min_correlation=0.01,
    max_numeric_features=None,
):
    """Подготовка признаков для обучения.

    Отбор признаков:
    - use_correlation_filter: отсекать признаки с |corr(признак, цена)| < min_correlation
      (сейчас min_correlation=0.01 — очень мягкий порог, отсекается только явный шум, поэтому ~99 признаков).
    - max_numeric_features: если задано (например 40), оставить только топ-N числовых признаков
      по убыванию модуля корреляции с ценой. Категориальные без отсечения. Сокращает число признаков.
    """
    target_col = 'price_actual' if 'price_actual' in df.columns else 'price'
    
    exclude_cols = [
        'cian_id', 'price', 'price_changes', 'price_from_changes', 
        'price_actual', 'publication_at', 'publication_date',
        'offer_created_at', 'offer_updated_at',
        'description', 'coordinates'
    ]
    
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    if use_correlation_filter:
        correlations = analyze_correlations(df, target_col, min_correlation)
        if correlations:
            low_corr_cols = [col for col, corr in correlations if abs(corr) < min_correlation]
            feature_cols = [col for col in feature_cols if col not in low_corr_cols]
            print(f"\nПосле фильтрации по корреляции (<{min_correlation}): {len(feature_cols)} признаков")
            # Опционально: оставить только топ-N числовых по корреляции (категориальные - все)
            if max_numeric_features is not None:
                corr_dict = dict(correlations)
                numeric_ordered = [c for c, _ in correlations if c in feature_cols]
                categorical_in_features = [c for c in feature_cols if c not in corr_dict]
                top_numeric = numeric_ordered[:max_numeric_features]
                feature_cols = top_numeric + categorical_in_features
                print(f"Оставлен топ-{max_numeric_features} числовых по корреляции + {len(categorical_in_features)} категориальных, всего {len(feature_cols)} признаков")
    
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
    
    print(f"\nПризнаков: {len(feature_cols)}")
    print(f"  Числовых: {len(numeric_cols)}")
    print(f"  Категориальных: {len(categorical_cols)}")
    
    return X, y, categorical_cols, numeric_cols, feature_cols


def train_catboost(X_train, y_train, X_test, y_test, categorical_cols, 
                   use_log_price=False, run_name="catboost_baseline"):
    """Обучение CatBoost модели."""
    print("\nОбучение CatBoost...")
    if use_log_price:
        print("  Используется логарифмирование цены")
        y_train_log = np.log1p(y_train)
        y_test_log = np.log1p(y_test)
    else:
        y_train_log = y_train
        y_test_log = y_test
    
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
        X_train, y_train_log,
        eval_set=(X_test, y_test_log),
        use_best_model=True,
        verbose=100
    )
    
    y_pred_train_log = model.predict(X_train)
    y_pred_test_log = model.predict(X_test)
    
    # Обратное преобразование, если использовалось логарифмирование
    if use_log_price:
        y_pred_train = np.expm1(y_pred_train_log)
        y_pred_test = np.expm1(y_pred_test_log)
    else:
        y_pred_train = y_pred_train_log
        y_pred_test = y_pred_test_log
    
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


def train_lightgbm(X_train, y_train, X_test, y_test, categorical_cols,
                     use_log_price=False, run_name="lightgbm_baseline"):
    """Обучение LightGBM модели."""
    print("\nОбучение LightGBM...")
    if use_log_price:
        print("  Используется логарифмирование цены")
        y_train_fit = np.log1p(y_train)
        y_test_fit = np.log1p(y_test)
    else:
        y_train_fit = y_train
        y_test_fit = y_test

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
        X_train_lgb, y_train_fit,
        eval_set=[(X_test_lgb, y_test_fit)],
        eval_metric='rmse',
        callbacks=[lambda env: None]
    )
    
    y_pred_train_log = model.predict(X_train_lgb)
    y_pred_test_log = model.predict(X_test_lgb)
    if use_log_price:
        y_pred_train = np.expm1(y_pred_train_log)
        y_pred_test = np.expm1(y_pred_test_log)
    else:
        y_pred_train = y_pred_train_log
        y_pred_test = y_pred_test_log
    
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


def train_xgboost(X_train, y_train, X_test, y_test, categorical_cols,
                  use_log_price=False, run_name="xgboost_baseline"):
    """Обучение XGBoost (hist). Категории - OrdinalEncoder (train/test согласованы, unknown в -1)."""
    print("\nОбучение XGBoost...")
    if use_log_price:
        print("  Используется логарифмирование цены")
        y_train_fit = np.log1p(y_train)
        y_test_fit = np.log1p(y_test)
    else:
        y_train_fit = y_train
        y_test_fit = y_test

    X_tr = X_train.copy()
    X_te = X_test.copy()

    enc = None
    cat_present = [c for c in categorical_cols if c in X_tr.columns]
    if cat_present:
        enc = OrdinalEncoder(
            handle_unknown="use_encoded_value",
            unknown_value=-1,
            encoded_missing_value=-1,
            dtype=np.float64,
        )
        X_tr[cat_present] = enc.fit_transform(X_tr[cat_present].astype(str))
        X_te[cat_present] = enc.transform(X_te[cat_present].astype(str))

    for col in X_tr.select_dtypes(include=['object']).columns:
        X_tr[col] = pd.to_numeric(X_tr[col], errors='coerce').fillna(0)
        X_te[col] = pd.to_numeric(X_te[col], errors='coerce').fillna(0)

    X_tr = X_tr.astype(np.float64)
    X_te = X_te.astype(np.float64)

    model = XGBRegressor(
        n_estimators=500,
        learning_rate=0.1,
        max_depth=6,
        random_state=42,
        n_jobs=-1,
        tree_method='hist',
    )

    model.fit(
        X_tr,
        y_train_fit,
        eval_set=[(X_te, y_test_fit)],
        verbose=100,
    )

    y_pred_train_log = model.predict(X_tr)
    y_pred_test_log = model.predict(X_te)
    if use_log_price:
        y_pred_train = np.expm1(y_pred_train_log)
        y_pred_test = np.expm1(y_pred_test_log)
    else:
        y_pred_train = y_pred_train_log
        y_pred_test = y_pred_test_log

    metrics_train = {
        'train_mae': mean_absolute_error(y_train, y_pred_train),
        'train_rmse': np.sqrt(mean_squared_error(y_train, y_pred_train)),
        'train_mape': calculate_mape(y_train, y_pred_train),
    }
    metrics_test = {
        'test_mae': mean_absolute_error(y_test, y_pred_test),
        'test_rmse': np.sqrt(mean_squared_error(y_test, y_pred_test)),
        'test_mape': calculate_mape(y_test, y_pred_test),
    }
    quantiles_test = calculate_quantiles(y_test, y_pred_test)

    print("\nМетрики XGBoost (Train):")
    print(f"  MAE: {metrics_train['train_mae']:.2f}")
    print(f"  RMSE: {metrics_train['train_rmse']:.2f}")
    print(f"  MAPE: {metrics_train['train_mape']:.2f}%")
    print("\nМетрики XGBoost (Test):")
    print(f"  MAE: {metrics_test['test_mae']:.2f}")
    print(f"  RMSE: {metrics_test['test_rmse']:.2f}")
    print(f"  MAPE: {metrics_test['test_mape']:.2f}%")
    print("\nКвантили ошибки (Test):")
    print(f"  P10: {quantiles_test['P10']:.2f}")
    print(f"  P50: {quantiles_test['P50']:.2f}")
    print(f"  P90: {quantiles_test['P90']:.2f}")

    model._X_train_prepared = X_tr
    model._xgb_ord_enc = enc
    model._xgb_cat_present = cat_present
    return model, metrics_train, metrics_test, quantiles_test


def log_model_to_mlflow(model, model_name, X_train, y_train, metrics_train, metrics_test, quantiles_test, use_log_price=False):
    """Логирование модели в MLflow."""
    with mlflow.start_run(run_name=f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        mlflow.log_param("model_name", model_name)
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_param("use_log_price", use_log_price)
        mlflow.set_tag("model_version", "v2" if use_log_price else "baseline")
        
        for key, value in metrics_train.items():
            mlflow.log_metric(key, value)
        
        for key, value in metrics_test.items():
            mlflow.log_metric(key, value)
        
        for key, value in quantiles_test.items():
            mlflow.log_metric(f"test_{key.lower()}", value)
        
        if model_name in ("lightgbm", "xgboost") and hasattr(model, '_X_train_prepared'):
            X_for_signature = model._X_train_prepared
        else:
            X_for_signature = X_train
        
        signature = infer_signature(X_for_signature, model.predict(X_for_signature))
        
        if model_name == "catboost":
            mlflow.catboost.log_model(model, "model", signature=signature)
        elif model_name == "lightgbm":
            mlflow.lightgbm.log_model(model, "model", signature=signature)
        elif model_name == "xgboost":
            import mlflow.xgboost as mlflow_xgb
            mlflow_xgb.log_model(model, "model", signature=signature)
        
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
    elif model_name == "xgboost":
        path_json = output_dir / f"{model_name}_baseline.json"
        model.save_model(str(path_json))
        print(f"Модель сохранена: {path_json}")
        return path_json
    
    print(f"Модель сохранена: {model_path}")
    return model_path


def train_baseline_models(
    data_dir=None,
    models_dir=None,
    use_log_price=False,
    max_numeric_features=None,
):
    """Основная функция обучения моделей.
    
    Args:
        data_dir: Директория с данными (train.csv, test.csv)
        models_dir: Директория для сохранения моделей
        use_log_price: Использовать ли логарифмирование цены (np.log1p)
        max_numeric_features: Если задано (например 40), оставить только топ-N числовых
            признаков по корреляции с ценой. Сокращает число признаков для обучения.
    """
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
    X_train, y_train, cat_cols_train, num_cols_train, feature_cols = prepare_features(
        train_df,
        use_correlation_filter=True,
        min_correlation=0.01,
        max_numeric_features=max_numeric_features,
    )
    X_test, y_test, _, _, _ = prepare_features(
        test_df, use_correlation_filter=False
    )
    
    X_test = X_test[X_train.columns]
    
    print(f"\nЦелевая переменная (Train):")
    print(f"  Медиана: {y_train.median():.2f}")
    print(f"  Среднее: {y_train.mean():.2f}")
    print(f"  Мин/Макс: {y_train.min():.2f} / {y_train.max():.2f}")
    if use_log_price:
        print(f"  Используется логарифмирование цены")
    
    init_mlflow()
    
    print("\n" + "="*60)
    cat_model, cat_metrics_train, cat_metrics_test, cat_quantiles = train_catboost(
        X_train, y_train, X_test, y_test, cat_cols_train, 
        use_log_price=use_log_price, run_name="catboost_baseline"
    )
    log_model_to_mlflow(
        cat_model, "catboost", X_train, y_train,
        cat_metrics_train, cat_metrics_test, cat_quantiles, use_log_price=use_log_price
    )
    save_model(cat_model, "catboost", models_dir)
    
    print("\n" + "="*60)
    lgb_model, lgb_metrics_train, lgb_metrics_test, lgb_quantiles = train_lightgbm(
        X_train, y_train, X_test, y_test, cat_cols_train,
        use_log_price=use_log_price, run_name="lightgbm_baseline"
    )
    log_model_to_mlflow(
        lgb_model, "lightgbm", X_train, y_train,
        lgb_metrics_train, lgb_metrics_test, lgb_quantiles, use_log_price=use_log_price
    )
    save_model(lgb_model, "lightgbm", models_dir)
    
    print("\n" + "="*60)
    xgb_model, xgb_metrics_train, xgb_metrics_test, xgb_quantiles = train_xgboost(
        X_train, y_train, X_test, y_test, cat_cols_train,
        use_log_price=use_log_price, run_name="xgboost_baseline"
    )
    log_model_to_mlflow(
        xgb_model, "xgboost", X_train, y_train,
        xgb_metrics_train, xgb_metrics_test, xgb_quantiles, use_log_price=use_log_price
    )
    save_model(xgb_model, "xgboost", models_dir)
    
    print("\n" + "="*60)
    print("Ансамбль (среднее предсказаний CatBoost + LightGBM + XGBoost), Test:")
    X_lgb_x = _prepare_x_for_lgb_xgb(X_test, cat_cols_train)
    X_xgb_x = _prepare_x_for_xgb_inference(X_test, xgb_model)
    raw_cat = cat_model.predict(X_test)
    raw_lgb = lgb_model.predict(X_lgb_x)
    raw_xgb = xgb_model.predict(X_xgb_x)
    if use_log_price:
        p_cat = np.expm1(raw_cat)
        p_lgb = np.expm1(raw_lgb)
        p_xgb = np.expm1(raw_xgb)
    else:
        p_cat, p_lgb, p_xgb = raw_cat, raw_lgb, raw_xgb
    p_ens = (p_cat + p_lgb + p_xgb) / 3.0
    ens_mae = mean_absolute_error(y_test, p_ens)
    ens_rmse = np.sqrt(mean_squared_error(y_test, p_ens))
    ens_mape = calculate_mape(y_test, p_ens)
    ens_q = calculate_quantiles(y_test, p_ens)
    print(f"  MAE: {ens_mae:.2f}")
    print(f"  RMSE: {ens_rmse:.2f}")
    print(f"  MAPE: {ens_mape:.2f}%")
    print(f"  P10/P50/P90 ошибки: {ens_q['P10']:.2f} / {ens_q['P50']:.2f} / {ens_q['P90']:.2f}")
    
    print("\n" + "="*60)
    print("Обучение завершено!")
    print(f"Модели сохранены в: {models_dir}")
    
    return cat_model, lgb_model, xgb_model


if __name__ == "__main__":
    # log1p(цена) обычно улучшает обобщение на длинном хвосте цен
    train_baseline_models(use_log_price=True)

